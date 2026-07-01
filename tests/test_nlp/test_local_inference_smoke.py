from __future__ import annotations

import os
from pathlib import Path

import pytest

import nlp.inference.confidence_router as confidence_router_module
from nlp.annotation.prompt_builder import annotation_input_id
from nlp.config import NLPConfig
from nlp.inference.confidence_router import ConfidenceRouter


SAMPLE_SENTENCE = "Pin trâu, camera chụp đêm đẹp, màn hình sáng"


class _FakeExtractor:
    def extract(self, sentence: str) -> list[dict]:
        return [
            {"aspect_label": "Pin", "segment_text": "Pin", "confidence": 0.98},
        ]


class _FakeClassifier:
    def classify(self, comment_text: str, aspect_label: str) -> tuple[str, float]:
        return "positive", 0.97


def test_confidence_router_model_schema_without_gemini() -> None:
    router = ConfidenceRouter(
        extractor=_FakeExtractor(),
        classifier=_FakeClassifier(),
        gemini_factory=lambda: pytest.fail("Gemini should not be initialized"),
    )

    results = router.annotate(SAMPLE_SENTENCE)

    assert results == [
        {
            "sentence": SAMPLE_SENTENCE,
            "aspect_label": "Pin",
            "segment_text": "Pin",
            "sentiment_label": "positive",
            "source": "model",
            "ner_confidence": 0.98,
            "sentiment_confidence": 0.97,
            "confidence": 0.97,
            "routing_decision": "model_accept",
        }
    ]


def test_confidence_router_none_aspect_does_not_call_classifier() -> None:
    class NoneExtractor:
        def extract(self, sentence: str) -> list[dict]:
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": 0.99}]

    class FailingClassifier:
        def classify(self, comment_text: str, aspect_label: str) -> tuple[str, float]:
            raise AssertionError("NONE aspect should not call PhoBERT")

    router = ConfidenceRouter(
        extractor=NoneExtractor(),
        classifier=FailingClassifier(),
        gemini_factory=lambda: pytest.fail("Gemini should not be initialized"),
    )

    assert router.annotate("Câu này chỉ hỏi chung thôi") == [
        {
            "sentence": "Câu này chỉ hỏi chung thôi",
            "aspect_label": "NONE",
            "segment_text": "",
            "sentiment_label": "neutral",
            "source": "model",
            "ner_confidence": 0.99,
            "sentiment_confidence": 1.0,
            "confidence": 0.99,
            "routing_decision": "model_accept",
        }
    ]


def test_confidence_router_batches_unique_fallback_sentences() -> None:
    class MixedExtractor:
        def extract(self, sentence: str) -> list[dict]:
            if sentence == "none":
                return [{"aspect_label": "NONE", "segment_text": "", "confidence": 0.99}]
            confidence = 0.60 if sentence == "low ner" else 0.95
            return [{"aspect_label": "Pin", "segment_text": "pin", "confidence": confidence}]

    class MixedClassifier:
        def classify(self, comment_text: str, aspect_label: str) -> tuple[str, float]:
            if comment_text == "low sentiment":
                return "negative", 0.60
            return "positive", 0.95

    class FakeGemini:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def annotate_all(self, sentences: list[str]) -> list[dict]:
            self.calls.append(sentences)
            return [
                {
                    "sentence": sentence,
                    "aspect_label": "Pin",
                    "segment_text": "pin",
                    "sentiment_label": "negative",
                }
                for sentence in sentences
            ]

    gemini = FakeGemini()
    router = ConfidenceRouter(
        extractor=MixedExtractor(),
        classifier=MixedClassifier(),
        gemini_factory=lambda: gemini,
    )

    results = router.annotate_many([
        "accepted",
        "none",
        "low ner",
        "low sentiment",
        "low ner",
    ])

    assert gemini.calls == [["low ner", "low sentiment"]]
    assert [items[0]["source"] for items in results] == [
        "model",
        "model",
        "gemini",
        "gemini",
        "gemini",
    ]


def test_confidence_router_uses_configured_gemini_batch_size(monkeypatch) -> None:
    created_batch_sizes: list[int] = []

    class LowConfidenceExtractor:
        def extract(self, sentence: str) -> list[dict]:
            return [{"aspect_label": "Pin", "segment_text": "pin", "confidence": 0.60}]

    class FakeGemini:
        def __init__(self, batch_size: int) -> None:
            created_batch_sizes.append(batch_size)

        def annotate_all(self, sentences: list[str]) -> list[dict]:
            return [{
                "sentence": sentences[0],
                "aspect_label": "Pin",
                "segment_text": "pin",
                "sentiment_label": "positive",
            }]

    monkeypatch.setattr(confidence_router_module, "GeminiAnnotator", FakeGemini)
    monkeypatch.setattr(
        confidence_router_module,
        "load_nlp_config",
        lambda: NLPConfig(gemini_batch_size=17),
    )
    router = ConfidenceRouter(
        extractor=LowConfidenceExtractor(),
        classifier=_FakeClassifier(),
    )

    assert router.annotate("low confidence")[0]["source"] == "gemini"
    assert created_batch_sizes == [17]


def test_confidence_router_returns_empty_list_when_gemini_omits_sentence() -> None:
    class LowConfidenceExtractor:
        def extract(self, sentence: str) -> list[dict]:
            return [{"aspect_label": "Pin", "segment_text": "pin", "confidence": 0.60}]

    class EmptyGemini:
        def annotate_all(self, sentences: list[str]) -> list[dict]:
            return []

    router = ConfidenceRouter(
        extractor=LowConfidenceExtractor(),
        classifier=_FakeClassifier(),
        gemini_factory=EmptyGemini,
    )

    assert router.annotate("missing result") == []


def test_confidence_router_maps_rewritten_gemini_sentence_by_input_id() -> None:
    class LowConfidenceExtractor:
        def extract(self, sentence: str) -> list[dict]:
            return [{"aspect_label": "Camera", "segment_text": "camera", "confidence": 0.60}]

    class RewritingGemini:
        def annotate_all(self, sentences: list[str]) -> list[dict]:
            return [{
                "input_id": annotation_input_id(sentences[0]),
                "sentence": "@ngango9888 camera của sony",
                "aspect_label": "Camera",
                "segment_text": "camera",
                "sentiment_label": "neutral",
            }]

    sentence = "@ngango9888  camera của sony nhưng tinh chỉ là app"
    router = ConfidenceRouter(
        extractor=LowConfidenceExtractor(),
        classifier=_FakeClassifier(),
        gemini_factory=RewritingGemini,
    )

    assert router.annotate(sentence)[0]["sentence"] == sentence


@pytest.mark.skipif(
    os.environ.get("RUN_NLP_SMOKE") != "1",
    reason="Set RUN_NLP_SMOKE=1 to load local PhoBERT/vELECTRA weights.",
)
def test_local_phobert_velectra_confidence_router_smoke() -> None:
    assert Path("models/phobert_sentiment/model.safetensors").exists()
    assert Path("models/velectra_aspect/model.safetensors").exists()

    router = ConfidenceRouter()
    results = router.annotate(SAMPLE_SENTENCE)

    aspect_labels = {item["aspect_label"] for item in results}
    assert {"Pin", "Camera", "Màn hình"}.issubset(aspect_labels)
    assert all(item["source"] == "model" for item in results)
    assert all(item["sentiment_label"] in {"positive", "negative", "neutral"} for item in results)
    assert all(0.0 <= item["ner_confidence"] <= 1.0 for item in results)
    assert all(0.0 <= item["sentiment_confidence"] <= 1.0 for item in results)
    assert all(0.0 <= item["confidence"] <= 1.0 for item in results)
