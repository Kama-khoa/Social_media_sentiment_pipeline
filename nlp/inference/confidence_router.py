from __future__ import annotations

import logging

from nlp.annotation.gemini_annotator import GeminiAnnotator
from nlp.inference.phobert_classifier import PhoBERTClassifier
from nlp.inference.velectra_extractor import VELECTRAExtractor

logger = logging.getLogger(__name__)

_THRESHOLD = 0.80


class ConfidenceRouter:
    def __init__(self) -> None:
        self._extractor = VELECTRAExtractor()
        self._classifier = PhoBERTClassifier()
        self._gemini = GeminiAnnotator(batch_size=1)

    def annotate(self, sentence: str) -> list[dict]:
        aspects = self._extractor.extract(sentence)

        results: list[dict] = []
        for aspect in aspects:
            if aspect["confidence"] < _THRESHOLD:
                return self._gemini_fallback(sentence)

            sentiment_label, sentiment_conf = self._classifier.classify(
                sentence, aspect["aspect_label"]
            )

            if sentiment_conf < _THRESHOLD:
                return self._gemini_fallback(sentence)

            results.append({
                "sentence": sentence,
                "aspect_label": aspect["aspect_label"],
                "segment_text": aspect["segment_text"],
                "sentiment_label": sentiment_label,
                "source": "model",
                "confidence": min(aspect["confidence"], sentiment_conf),
            })

        return results

    def _gemini_fallback(self, sentence: str) -> list[dict]:
        logger.info("Low confidence — routing to Gemini: %.50s", sentence)
        return [{**r, "source": "gemini"} for r in self._gemini.annotate_all([sentence])]
