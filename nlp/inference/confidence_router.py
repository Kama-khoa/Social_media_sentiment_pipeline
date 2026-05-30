from __future__ import annotations

import logging
from typing import Callable

from nlp.annotation.gemini_annotator import GeminiAnnotator
from nlp.inference.phobert_classifier import PhoBERTClassifier
from nlp.inference.velectra_extractor import VELECTRAExtractor

logger = logging.getLogger(__name__)

_THRESHOLD = 0.70


class ConfidenceRouter:
    def __init__(
        self,
        extractor: VELECTRAExtractor | None = None,
        classifier: PhoBERTClassifier | None = None,
        confidence_threshold: float = _THRESHOLD,
        gemini_factory: Callable[[], GeminiAnnotator] | None = None,
    ) -> None:
        self._extractor = extractor or VELECTRAExtractor()
        self._classifier = classifier or PhoBERTClassifier()
        self._confidence_threshold = confidence_threshold
        self._gemini_factory = gemini_factory or (lambda: GeminiAnnotator(batch_size=1))
        self._gemini: GeminiAnnotator | None = None

    def annotate(self, sentence: str) -> list[dict]:
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
                return self._gemini_fallback(sentence)

            sentiment_label, sentiment_conf = self._classifier.classify(
                sentence, aspect["aspect_label"]
            )
            sentiment_conf = float(sentiment_conf)

            if sentiment_conf < self._confidence_threshold:
                return self._gemini_fallback(sentence)

            final_conf = min(ner_conf, sentiment_conf)
            results.append({
                "sentence": sentence,
                "aspect_label": aspect["aspect_label"],
                "segment_text": aspect["segment_text"],
                "sentiment_label": sentiment_label,
                "source": "model",
                "ner_confidence": ner_conf,
                "sentiment_confidence": sentiment_conf,
                "confidence": final_conf,
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

    def _gemini_fallback(self, sentence: str) -> list[dict]:
        logger.info("Low confidence — routing to Gemini: %.50s", sentence)
        if self._gemini is None:
            self._gemini = self._gemini_factory()
        return [{**r, "source": "gemini"} for r in self._gemini.annotate_all([sentence])]
