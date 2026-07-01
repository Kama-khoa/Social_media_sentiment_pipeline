from __future__ import annotations

import logging
import os
import threading

from google import genai

from nlp.annotation.gemini_annotator import (
    GeminiAnnotator,
    _DailyBudget,
    _FREE_TIER_LIMITS,
    _RATE_LIMIT_ERRORS,
    _RateLimiter,
)

logger = logging.getLogger(__name__)


class GeminiQuotaExhaustedError(RuntimeError):
    pass


class GeminiGateway:
    """Shared Gemini model routing and free-tier throttling policy."""

    def __init__(self, api_key: str | None = None, client=None) -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = client or (genai.Client(api_key=resolved_key) if resolved_key else None)
        self._limiters = {
            model: _RateLimiter(limits["rpm"]) for model, limits in _FREE_TIER_LIMITS.items()
        }
        self._daily_budgets = {
            model: _DailyBudget(limits["rpd"]) for model, limits in _FREE_TIER_LIMITS.items()
        }
        self._available_models = list(GeminiAnnotator._MODELS_TO_TRY)
        self.last_model: str | None = None
        self._lock = threading.Lock()

    def generate(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        import time

        last_exc: Exception | None = None
        now = time.monotonic()
        models_to_try = []
        for model_name in list(self._available_models):
            with self._lock:
                budget = self._daily_budgets[model_name]
                if not budget.can_use():
                    if model_name in self._available_models:
                        self._available_models.remove(model_name)
                    logger.warning("Model %s exhausted its daily request budget", model_name)
                    continue
                models_to_try.append(model_name)

        if not models_to_try:
            raise GeminiQuotaExhaustedError("All Gemini models exhausted RPD quota.")

        available_now = [m for m in models_to_try if m not in self._limiters or self._limiters[m]._blocked_until <= now]
        blocked = [m for m in models_to_try if m in self._limiters and self._limiters[m]._blocked_until > now]
        blocked.sort(key=lambda m: self._limiters[m]._blocked_until)
        ordered_models = available_now + blocked

        for model_name in ordered_models:
            with self._lock:
                limiter = self._limiters[model_name]
                budget = self._daily_budgets[model_name]

            limiter.wait(model_name)

            try:
                response = self._client.models.generate_content(model=model_name, contents=prompt)
                with self._lock:
                    budget.increment()
                self.last_model = model_name
                return response.text
            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = any(marker in exc_str for marker in _RATE_LIMIT_ERRORS)
                is_not_found = "404" in exc_str or "not found" in exc_str or "not_found" in exc_str
                
                if is_rate_limit or is_not_found:
                    with self._lock:
                        if is_rate_limit:
                            limiter.block_for_cooldown()
                        if is_not_found:
                            if model_name in self._available_models:
                                self._available_models.remove(model_name)
                    last_exc = exc
                    try:
                        available_list = list(self._available_models)
                        if available_list:
                            next_model_idx = ordered_models.index(model_name) + 1
                            if next_model_idx < len(ordered_models):
                                next_model = ordered_models[next_model_idx]
                                reason_msg = "rate limited" if is_rate_limit else "not found (404)"
                                logger.warning("Model %s %s, switching to fallback model %s", model_name, reason_msg, next_model)
                                print(f"\n[Gateway] Model {model_name} {reason_msg}. Switching to fallback model {next_model}...")
                    except Exception:
                        pass
                    continue
                raise

        raise GeminiQuotaExhaustedError("All Gemini models in fallback chain exhausted") from last_exc


