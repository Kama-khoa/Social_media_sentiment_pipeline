from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import date
from pathlib import Path

from google import genai
from dotenv import load_dotenv
from underthesea import word_tokenize

from nlp.annotation.prompt_builder import PromptBuilder, annotation_input_id
from nlp.annotation.prompt_config import ASPECT_LABELS, SENTIMENT_LABELS

load_dotenv()

_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logger = logging.getLogger(__name__)

# Free-tier rate limits per model.
# Source: https://ai.google.dev/gemini-api/docs/rate-limits
# Verify your actual limits at: https://aistudio.google.com/rate-limit
_FREE_TIER_LIMITS: dict[str, dict[str, int]] = {
    "gemini-3.1-flash-lite": {"rpm": 15,  "rpd": 500, "tpm": 250000},
    "gemini-3.5-flash": {"rpm": 5,  "rpd": 20, "tpm": 250000},
    "gemini-3-flash-preview": {"rpm": 5,  "rpd": 20, "tpm": 250000},
    "gemini-2.5-flash-lite": {"rpm": 10,  "rpd": 20,  "tpm":   250000},
    "gemini-2.5-flash":      {"rpm": 5,  "rpd": 20, "tpm": 250000},
    "gemma-4-26b-a4b-it": {"rpm": 15, "rpd": 1500, "tpm": 250000},
    "gemma-4-31b-it": {"rpm": 15, "rpd": 1500, "tpm": 250000},
}

# Sử dụng 75% RPM limit để có buffer cho drift thời gian
_SAFETY_FACTOR = 0.75

# Sau khi nhận 429, block model này trong 70s trước khi thử lại
_COOLDOWN_AFTER_429: float = 70.0

_RATE_LIMIT_ERRORS = frozenset(
    ["429", "quota", "exhausted", "resource_exhausted", "503", "unavailable", "overloaded"]
)


class _RateLimiter:
    """Giới hạn RPM và xử lý 429 cooldown per-model."""

    def __init__(self, rpm: int) -> None:
        effective_rpm = rpm * _SAFETY_FACTOR
        self._min_interval: float = 60.0 / effective_rpm
        self._last_call: float = 0.0
        self._blocked_until: float = 0.0
        self._lock = threading.Lock()

    def wait(self, model_name: str) -> None:
        with self._lock:
            now = time.monotonic()
            cooldown_remaining = self._blocked_until - now
            
        if cooldown_remaining > 0:
            logger.info(
                "Model %s đang trong 429 cooldown, chờ %.0fs...",
                model_name, cooldown_remaining,
            )
            time.sleep(cooldown_remaining)

        with self._lock:
            now = time.monotonic()
            to_sleep = self._min_interval - (now - self._last_call)
            if to_sleep > 0:
                self._last_call = now + to_sleep
            else:
                self._last_call = now
                to_sleep = 0.0

        if to_sleep > 0:
            logger.debug(
                "Rate limiter [%s]: chờ %.1fs (%.1f RPM target)",
                model_name, to_sleep, 60.0 / self._min_interval,
            )
            time.sleep(to_sleep)

    def block_for_cooldown(self) -> None:
        """Gọi sau khi nhận 429 — block model này trong _COOLDOWN_AFTER_429 giây."""
        with self._lock:
            self._blocked_until = time.monotonic() + _COOLDOWN_AFTER_429


class _DailyBudget:
    """Theo dõi số requests đã dùng trong ngày để tránh vượt RPD limit."""

    def __init__(self, rpd: int) -> None:
        self._rpd = rpd
        self._count = 0
        self._date = date.today()

    def can_use(self) -> bool:
        today = date.today()
        if today != self._date:
            self._count = 0
            self._date = today
        return self._count < self._rpd

    def increment(self) -> None:
        self._count += 1

    @property
    def remaining(self) -> int:
        return max(0, self._rpd - self._count)


class GeminiAnnotator:
    _MODELS_TO_TRY = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemma-4-26b-a4b-it",
        "gemma-4-31b-it",
    ]

    _VALID_ASPECTS = set(ASPECT_LABELS + ["NONE"])
    _VALID_SENTIMENTS = set(SENTIMENT_LABELS)
    _REQUIRED_KEYS = {"sentence", "aspect_label", "segment_text", "sentiment_label"}

    def __init__(self, batch_size: int = 50) -> None:
        self._batch_size = batch_size
        self._prompt_builder = PromptBuilder()

        self._limiters: dict[str, _RateLimiter] = {
            model: _RateLimiter(limits["rpm"])
            for model, limits in _FREE_TIER_LIMITS.items()
        }
        self._daily_budgets: dict[str, _DailyBudget] = {
            model: _DailyBudget(limits["rpd"])
            for model, limits in _FREE_TIER_LIMITS.items()
        }
        # List mutable — model hết RPD sẽ bị xóa vĩnh viễn khỏi đây.
        # Các batch sau bắt đầu thẳng từ model đầu tiên còn lại, không check lại model đã cạn.
        self._available_models: list[str] = list(self._MODELS_TO_TRY)

        if _GEMINI_API_KEY:
            self._client = genai.Client(api_key=_GEMINI_API_KEY)
        else:
            logger.warning("GEMINI_API_KEY không được tìm thấy trong biến môi trường!")
            self._client = None

    def _max_cooldown_remaining(self) -> float:
        """Trả về số giây cooldown còn lại lớn nhất trong số các model available."""
        now = time.monotonic()
        if not self._available_models:
            return 0.0
        return max(
            max(0.0, self._limiters[m]._blocked_until - now)
            for m in self._available_models
            if m in self._limiters
        )

    def annotate_all(
        self,
        sentences: list[str],
        checkpoint_file: Path | None = None,
    ) -> list[dict]:
        done_sentences: set[str] = set()
        results: list[dict] = []

        if checkpoint_file and Path(checkpoint_file).exists():
            with open(checkpoint_file, encoding="utf-8") as f:
                results = json.load(f)
            done_sentences = {r["sentence"] for r in results}
            logger.info(
                "Checkpoint: %d items (%d sentences đã xong), tiếp tục từ điểm dừng",
                len(results), len(done_sentences),
            )

        pending = [s for s in sentences if s not in done_sentences]
        total_batches = -(-len(pending) // self._batch_size)
        logger.info("Còn %d/%d câu cần annotation (%d batch)", len(pending), len(sentences), total_batches)

        for i in range(0, len(pending), self._batch_size):
            batch = pending[i : i + self._batch_size]
            batch_idx = i // self._batch_size + 1

            last_exc: Exception | None = None
            items: list[dict] = []
            remaining = batch
            for attempt in range(3):
                try:
                    round_items = self._annotate_batch(remaining)
                    items.extend(round_items)
                    remaining = self._missing_sentences(remaining, round_items)
                    last_exc = None
                    if remaining and attempt < 2:
                        logger.warning(
                            "Batch %d/%d thiếu %d câu; retry riêng các câu chưa có annotation",
                            batch_idx,
                            total_batches,
                            len(remaining),
                        )
                        continue
                    break
                except Exception as exc:
                    last_exc = exc
                    # Chờ ít nhất bằng cooldown còn lại của tất cả model + 5s buffer.
                    # Tránh retry khi model vẫn đang trong cooldown (bug cũ: 60s wait < 70s cooldown).
                    base_wait = 65 * (attempt + 1)
                    max_cooldown = self._max_cooldown_remaining()
                    actual_wait = max(base_wait, max_cooldown + 5.0)
                    logger.warning(
                        "Batch %d/%d attempt %d/3 thất bại: %s. "
                        "Cooldown còn %.0fs — retry trong %.0fs...",
                        batch_idx, total_batches, attempt + 1, exc,
                        max_cooldown, actual_wait,
                    )
                    if attempt < 2:
                        time.sleep(actual_wait)

            if last_exc:
                logger.error(
                    "Batch %d/%d bỏ qua sau 3 lần thất bại: %s",
                    batch_idx, total_batches, last_exc,
                )
            if remaining:
                logger.warning(
                    "Batch %d/%d vẫn thiếu %d câu sau tối đa 3 lần gọi Gemini",
                    batch_idx,
                    total_batches,
                    len(remaining),
                )
            results.extend(items)
            if checkpoint_file:
                Path(checkpoint_file).parent.mkdir(parents=True, exist_ok=True)
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info("Batch %d/%d: %d items OK", batch_idx, total_batches, len(items))

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
        normalized = [
            normalized_item
            for item in valid
            if (normalized_item := self._normalize_item_sentence(item, sentences)) is not None
        ]
        return [self._attach_bio_tags(item) for item in normalized]

    def _normalize_item_sentence(
        self,
        item: dict,
        expected_sentences: list[str],
    ) -> dict | None:
        expected_by_input_id = {
            annotation_input_id(sentence): sentence for sentence in expected_sentences
        }
        sentence = str(item["sentence"])
        original_sentence = expected_by_input_id.get(str(item.get("input_id", "")))
        if original_sentence is None and sentence in expected_sentences:
            original_sentence = sentence
        if original_sentence is None:
            logger.warning("Ignoring Gemini result for unexpected sentence: %.50s", sentence)
            return None
        return {**item, "sentence": original_sentence}

    def _missing_sentences(
        self,
        expected_sentences: list[str],
        items: list[dict],
    ) -> list[str]:
        annotated_sentences = {str(item["sentence"]) for item in items}
        return [
            sentence for sentence in expected_sentences if sentence not in annotated_sentences
        ]

    def _call_llm_with_fallback(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("GEMINI_API_KEY chưa được thiết lập, không thể gọi API")

        last_exc: Exception | None = None

        models_to_try = list(self._available_models)
        
        for model_name in models_to_try.copy():
            budget = self._daily_budgets.get(model_name)
            if budget and not budget.can_use():
                self._available_models.remove(model_name)
                models_to_try.remove(model_name)
                logger.warning(
                    "Model %s hết RPD quota hôm nay — loại khỏi session. "
                    "Còn lại: [%s]",
                    model_name,
                    ", ".join(self._available_models) if self._available_models else "không còn model nào",
                )

        if not models_to_try:
            raise RuntimeError("All Gemini models exhausted RPD quota.")

        now = time.monotonic()
        available_now = [m for m in models_to_try if m not in self._limiters or self._limiters[m]._blocked_until <= now]
        blocked = [m for m in models_to_try if m in self._limiters and self._limiters[m]._blocked_until > now]
        
        blocked.sort(key=lambda m: self._limiters[m]._blocked_until)
        ordered_models = available_now + blocked

        for model_name in ordered_models:
            limiter = self._limiters.get(model_name)
            if limiter:
                limiter.wait(model_name)

            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if model_name in self._daily_budgets:
                    budget = self._daily_budgets[model_name]
                    budget.increment()
                    remaining = budget.remaining
                    if remaining <= 100 or remaining % 200 == 0:
                        logger.info(
                            "RPD budget [%s]: còn %d/%d requests hôm nay",
                            model_name, remaining, _FREE_TIER_LIMITS[model_name]["rpd"],
                        )
                return response.text
            except Exception as exc:
                msg = str(exc).lower()
                logger.warning(
                    "Model %s lỗi — raw error: %s",
                    model_name, str(exc)[:500],
                )
                if any(err in msg for err in _RATE_LIMIT_ERRORS):
                    if limiter:
                        limiter.block_for_cooldown()
                    last_exc = exc
                    try:
                        next_model_idx = ordered_models.index(model_name) + 1
                        if next_model_idx < len(ordered_models):
                            next_model = ordered_models[next_model_idx]
                            logger.warning("Model %s rate limited, switching to fallback model %s", model_name, next_model)
                            print(f"\n[Annotator] Model {model_name} rate limited. Switching to fallback model {next_model}...")
                    except ValueError:
                        pass
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
