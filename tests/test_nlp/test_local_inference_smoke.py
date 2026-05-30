from __future__ import annotations

import os
from pathlib import Path

import pytest

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
