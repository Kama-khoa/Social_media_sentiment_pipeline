from __future__ import annotations

import json
import logging
import os
import re
import time

from google import genai
from dotenv import load_dotenv
from underthesea import word_tokenize

from nlp.annotation.prompt_builder import PromptBuilder
from nlp.annotation.prompt_config import ASPECT_LABELS, SENTIMENT_LABELS

load_dotenv()

_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logger = logging.getLogger(__name__)


class GeminiAnnotator:
    _MODELS_TO_TRY = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash", # Dự phòng cuối cùng (1500 RPD)
    ]

    _VALID_ASPECTS = set(ASPECT_LABELS + ["NONE"])
    _VALID_SENTIMENTS = set(SENTIMENT_LABELS)
    _REQUIRED_KEYS = {"sentence", "aspect_label", "segment_text", "sentiment_label"}

    def __init__(self, batch_size: int = 50) -> None:
        self._batch_size = batch_size
        self._prompt_builder = PromptBuilder()

        if _GEMINI_API_KEY:
            self._client = genai.Client(api_key=_GEMINI_API_KEY)
        else:
            logger.warning("GEMINI_API_KEY không được tìm thấy trong biến môi trường!")
            self._client = None

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
                # Ngủ 15 giây để khống chế tốc độ ở mức ~4 Requests Per Minute (bảo vệ giới hạn 5 RPM)
                logger.info("Nghỉ 15 giây để tránh lỗi Rate Limit...")
                time.sleep(15)
            except Exception as exc:
                logger.error("Batch %d–%d failed, skipping: %s", i, i + len(batch), exc)
        return results

    def _annotate_batch(self, sentences: list[str]) -> list[dict]:
        prompt = self._prompt_builder.build_annotation_prompt(sentences)
        raw_text = self._call_llm_with_fallback(prompt)
        parsed = self._parse_json_response(raw_text)
        valid = [item for item in parsed if self._is_valid_item(item)]
        if len(valid) < len(parsed):
            logger.warning(
                "Dropped %d invalid items from batch (kept %d)",
                len(parsed) - len(valid), len(valid),
            )
        return [self._attach_bio_tags(item) for item in valid]

    def _call_llm_with_fallback(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("GEMINI_API_KEY chưa được thiết lập, không thể gọi API")

        last_exc: Exception | None = None

        for model_name in self._MODELS_TO_TRY:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text
            except Exception as exc:
                msg = str(exc).lower()
                # Bắt lỗi 429 (Rate limit), Quota, hoặc 503 (Server quá tải)
                if any(err in msg for err in ["429", "quota", "exhausted", "resource_exhausted", "503", "unavailable"]):
                    logger.warning("Model %s bị rate limit/hết quota/quá tải. Chuyển sang model tiếp theo...", model_name)
                    last_exc = exc
                    time.sleep(1)
                    continue
                raise exc

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
