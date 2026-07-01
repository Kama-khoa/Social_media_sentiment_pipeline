from __future__ import annotations

import logging
from typing import Callable

from nlp.annotation.gemini_annotator import GeminiAnnotator
from nlp.annotation.prompt_builder import annotation_input_id
from nlp.config import load_nlp_config
from nlp.inference.phobert_classifier import PhoBERTClassifier
from nlp.inference.velectra_extractor import VELECTRAExtractor

logger = logging.getLogger(__name__)


class ConfidenceRouter:
    def __init__(
        self,
        extractor: VELECTRAExtractor | None = None,
        classifier: PhoBERTClassifier | None = None,
        confidence_threshold: float | None = None,
        gemini_batch_size: int | None = None,
        gemini_factory: Callable[[], GeminiAnnotator] | None = None,
    ) -> None:
        config = load_nlp_config()
        self._extractor = extractor or VELECTRAExtractor()
        self._classifier = classifier or PhoBERTClassifier()
        self._confidence_threshold = (
            config.confidence_threshold
            if confidence_threshold is None
            else confidence_threshold
        )
        self._gemini_batch_size = (
            config.gemini_batch_size if gemini_batch_size is None else gemini_batch_size
        )
        self._gemini_factory = gemini_factory or (
            lambda: GeminiAnnotator(batch_size=self._gemini_batch_size)
        )
        self._gemini: GeminiAnnotator | None = None

    def annotate(self, sentence: str) -> list[dict]:
        return self.annotate_many([sentence])[0]

    def annotate_many(self, sentences: list[str]) -> list[list[dict]]:
        local_results = self.annotate_local_many(sentences)
        fallback_sentences: list[str] = []

        for sentence, annotations in zip(sentences, local_results):
            if annotations is None:
                fallback_sentences.append(sentence)

        unique_fallback_sentences = list(dict.fromkeys(fallback_sentences))
        gemini_results = self.annotate_gemini_many(unique_fallback_sentences)

        return [
            annotations if annotations is not None else gemini_results.get(sentence, [])
            for sentence, annotations in zip(sentences, local_results)
        ]

    def annotate_local_many(self, sentences: list[str]) -> list[list[dict] | None]:
        return [self._annotate_local(sentence) for sentence in sentences]

    def annotate_gemini_many(self, sentences: list[str]) -> dict[str, list[dict]]:
        return self._gemini_fallback(list(dict.fromkeys(sentences)))

    def _annotate_local(self, sentence: str) -> list[dict] | None:
        aspects = self._extractor.extract(sentence)
        results: list[dict] = []

        for aspect in aspects:
            ner_conf = float(aspect["confidence"])
            if aspect["aspect_label"] == "NONE":
                results.append({
                    "sentence": sentence,
                    "aspect_label": "NONE",
                    "segment_text": "",
                    "sentiment_label": "neutral",
                    "source": "model",
                    "ner_confidence": ner_conf,
                    "sentiment_confidence": 1.0,
                    "confidence": ner_conf,
                    "routing_decision": "model_accept",
                })
                continue

            if ner_conf < self._confidence_threshold:
                return None

            sentiment_label, sentiment_conf = self._classifier.classify(
                sentence, aspect["aspect_label"]
            )
            sentiment_conf = float(sentiment_conf)
            if sentiment_conf < self._confidence_threshold:
                return None

            results.append({
                "sentence": sentence,
                "aspect_label": aspect["aspect_label"],
                "segment_text": aspect["segment_text"],
                "sentiment_label": sentiment_label,
                "source": "model",
                "ner_confidence": ner_conf,
                "sentiment_confidence": sentiment_conf,
                "confidence": min(ner_conf, sentiment_conf),
                "routing_decision": "model_accept",
            })

        return results

    def diagnose_local(self, sentence: str) -> list[dict]:
        aspects = self._extractor.extract(sentence)
        results: list[dict] = []

        for aspect in aspects:
            ner_conf = float(aspect["confidence"])
            aspect_label = aspect["aspect_label"]

            if aspect_label == "NONE":
                results.append({
                    "sentence": sentence,
                    "aspect_label": "NONE",
                    "segment_text": "",
                    "ner_confidence": ner_conf,
                    "sentiment_label": "neutral",
                    "sentiment_confidence": 1.0,
                    "confidence": ner_conf,
                    "would_fallback": False,
                    "fallback_reason": "",
                })
                continue

            sentiment_label, sentiment_conf = self._classifier.classify(sentence, aspect_label)
            sentiment_conf = float(sentiment_conf)
            final_conf = min(ner_conf, sentiment_conf)

            fallback_reason = ""
            if ner_conf < self._confidence_threshold:
                fallback_reason = "ner_confidence_below_threshold"
            elif sentiment_conf < self._confidence_threshold:
                fallback_reason = "sentiment_confidence_below_threshold"

            results.append({
                "sentence": sentence,
                "aspect_label": aspect_label,
                "segment_text": aspect["segment_text"],
                "ner_confidence": ner_conf,
                "sentiment_label": sentiment_label,
                "sentiment_confidence": sentiment_conf,
                "confidence": final_conf,
                "would_fallback": bool(fallback_reason),
                "fallback_reason": fallback_reason,
            })

        return results

    def _gemini_fallback(self, sentences: list[str]) -> dict[str, list[dict]]:
        if not sentences:
            return {}

        logger.info("Routing %d low-confidence sentences to Gemini", len(sentences))
        if self._gemini is None:
            self._gemini = self._gemini_factory()

        expected_sentences = set(sentences)
        expected_by_input_id = {
            annotation_input_id(sentence): sentence for sentence in sentences
        }
        grouped: dict[str, list[dict]] = {}
        for result in self._gemini.annotate_all(sentences):
            sentence = str(result["sentence"])
            original_sentence = expected_by_input_id.get(str(result.get("input_id", "")))
            if original_sentence is None and sentence in expected_sentences:
                original_sentence = sentence
            if original_sentence is None:
                logger.warning("Ignoring Gemini result for unexpected sentence: %.50s", sentence)
                continue
            grouped.setdefault(original_sentence, []).append({
                **result,
                "sentence": original_sentence,
                "source": "gemini",
            })

        missing = [sentence for sentence in sentences if sentence not in grouped]
        if missing:
            logger.warning(
                "Gemini returned no annotations for %d/%d low-confidence sentences",
                len(missing),
                len(sentences),
            )
        return grouped
