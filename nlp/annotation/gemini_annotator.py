from __future__ import annotations

import json
import logging
import os
import re

import requests
from dotenv import load_dotenv
from underthesea import word_tokenize

from nlp.annotation.prompt_builder import PromptBuilder

load_dotenv()

_GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

logger = logging.getLogger(__name__)


class GeminiAnnotator:
    _MODEL_FALLBACK_CHAIN = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]
    _BASE_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        "/{model}:generateContent"
    )
    _VALID_ASPECTS = {"Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá", "NONE"}
    _VALID_SENTIMENTS = {"positive", "negative", "neutral"}
    _REQUIRED_KEYS = {"sentence", "aspect_label", "segment_text", "sentiment_label"}

    def __init__(self, batch_size: int = 50) -> None:
        self._batch_size = batch_size
        self._prompt_builder = PromptBuilder()

    def annotate_all(self, sentences: list[str]) -> list[dict]:
        results: list[dict] = []
        for i in range(0, len(sentences), self._batch_size):
            batch = sentences[i : i + self._batch_size]
            try:
                items = self._annotate_batch(batch)
                results.extend(items)
                logger.info(
                    "Batch %d–%d: %d/%d items annotated",
                    i, i + len(batch), len(items), len(batch),
                )
            except Exception as exc:
                logger.error("Batch %d–%d failed, skipping: %s", i, i + len(batch), exc)
        return results

    def _annotate_batch(self, sentences: list[str]) -> list[dict]:
        prompt = self._prompt_builder.build_annotation_prompt(sentences)
        raw_text = self._post_with_fallback(prompt)
        parsed = self._parse_json_response(raw_text)
        valid = [item for item in parsed if self._is_valid_item(item)]
        if len(valid) < len(parsed):
            logger.warning(
                "Dropped %d invalid items from batch (kept %d)",
                len(parsed) - len(valid), len(valid),
            )
        return [self._attach_bio_tags(item) for item in valid]

    def _post_with_fallback(self, prompt: str) -> str:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        last_exc: Exception | None = None
        for model in self._MODEL_FALLBACK_CHAIN:
            url = self._BASE_URL.format(model=model) + f"?key={_GEMINI_API_KEY}"
            try:
                resp = requests.post(url, json=payload, timeout=60)
                if resp.status_code == 429:
                    logger.warning("Quota exceeded for %s, switching to next model", model)
                    last_exc = RuntimeError(f"Quota exceeded: {model}")
                    continue
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except requests.RequestException as exc:
                logger.warning("Request failed for model %s: %s", model, exc)
                last_exc = exc
        raise RuntimeError("All Gemini models in fallback chain exhausted") from last_exc

    def _parse_json_response(self, text: str) -> list[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Cannot parse Gemini response as JSON: {text[:300]}")

    def _is_valid_item(self, item: dict) -> bool:
        if not isinstance(item, dict):
            return False
        if not self._REQUIRED_KEYS.issubset(item.keys()):
            return False
        return (
            item["aspect_label"] in self._VALID_ASPECTS
            and item["sentiment_label"] in self._VALID_SENTIMENTS
        )

    def _attach_bio_tags(self, item: dict) -> dict:
        bio_tags = self._build_bio_tags(
            item["sentence"], item["aspect_label"], item["segment_text"]
        )
        return {**item, "bio_tags": bio_tags}

    def _build_bio_tags(
        self, sentence: str, aspect_label: str, segment_text: str
    ) -> list[str]:
        tokens: list[str] = word_tokenize(sentence)
        if aspect_label == "NONE" or not segment_text.strip():
            return ["O"] * len(tokens)

        seg_lower = segment_text.strip().lower()
        bio = ["O"] * len(tokens)

        for start in range(len(tokens)):
            for length in range(1, len(tokens) - start + 1):
                span = " ".join(tokens[start : start + length]).lower()
                if span == seg_lower:
                    bio[start] = f"B-{aspect_label}"
                    for k in range(1, length):
                        bio[start + k] = f"I-{aspect_label}"
                    return bio

        for start in range(len(tokens)):
            for length in range(1, len(tokens) - start + 1):
                span = " ".join(tokens[start : start + length]).lower()
                if seg_lower in span or span in seg_lower:
                    bio[start] = f"B-{aspect_label}"
                    for k in range(1, length):
                        bio[start + k] = f"I-{aspect_label}"
                    return bio

        return bio
