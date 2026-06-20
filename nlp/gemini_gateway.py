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

        last_exc: Exception | None = None
        for model_name in list(self._available_models):
            with self._lock:
                budget = self._daily_budgets[model_name]
                if not budget.can_use():
                    if model_name in self._available_models:
                        self._available_models.remove(model_name)
                    logger.warning("Model %s exhausted its daily request budget", model_name)
                    continue

                limiter = self._limiters[model_name]
                limiter.wait(model_name)

            try:
                response = self._client.models.generate_content(model=model_name, contents=prompt)
                with self._lock:
                    budget.increment()
                self.last_model = model_name
                return response.text
            except Exception as exc:
                if any(marker in str(exc).lower() for marker in _RATE_LIMIT_ERRORS):
                    with self._lock:
                        limiter.block_for_cooldown()
                    last_exc = exc
                    logger.warning("Model %s rate limited, trying fallback model", model_name)
                    continue
                raise

        raise RuntimeError("All Gemini models in fallback chain exhausted") from last_exc

