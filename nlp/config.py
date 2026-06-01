from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_CONFIDENCE_THRESHOLD = 0.70
_DEFAULT_GEMINI_BATCH_SIZE = 50
_DEFAULT_BQ_WRITE_BATCH_SIZE = 50
_DEFAULT_BQ_WRITE_MAX_RETRIES = 2
_DEFAULT_BQ_WRITE_RETRY_BASE_SECONDS = 2.0


@dataclass(frozen=True)
class NLPConfig:
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD
    gemini_batch_size: int = _DEFAULT_GEMINI_BATCH_SIZE
    bq_write_batch_size: int = _DEFAULT_BQ_WRITE_BATCH_SIZE
    bq_write_max_retries: int = _DEFAULT_BQ_WRITE_MAX_RETRIES
    bq_write_retry_base_seconds: float = _DEFAULT_BQ_WRITE_RETRY_BASE_SECONDS

    def __post_init__(self) -> None:
        if self.gemini_batch_size <= 0:
            raise ValueError("gemini_batch_size must be greater than zero")
        if self.bq_write_batch_size <= 0:
            raise ValueError("bq_write_batch_size must be greater than zero")
        if self.bq_write_max_retries < 0:
            raise ValueError("bq_write_max_retries must not be negative")
        if self.bq_write_retry_base_seconds < 0:
            raise ValueError("bq_write_retry_base_seconds must not be negative")


def load_nlp_config(config_path: str | Path | None = None) -> NLPConfig:
    resolved = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).parent.parent / "config" / "pipeline_config.yaml"
    )
    with resolved.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    nlp = raw.get("nlp") or {}
    return NLPConfig(
        confidence_threshold=float(
            nlp.get("confidence_threshold", _DEFAULT_CONFIDENCE_THRESHOLD)
        ),
        gemini_batch_size=int(nlp.get("gemini_batch_size", _DEFAULT_GEMINI_BATCH_SIZE)),
        bq_write_batch_size=int(
            nlp.get("bq_write_batch_size", _DEFAULT_BQ_WRITE_BATCH_SIZE)
        ),
        bq_write_max_retries=int(
            nlp.get("bq_write_max_retries", _DEFAULT_BQ_WRITE_MAX_RETRIES)
        ),
        bq_write_retry_base_seconds=float(
            nlp.get(
                "bq_write_retry_base_seconds",
                _DEFAULT_BQ_WRITE_RETRY_BASE_SECONDS,
            )
        ),
    )
