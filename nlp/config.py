from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_CONFIDENCE_THRESHOLD = 0.70
_DEFAULT_GEMINI_BATCH_SIZE = 50


@dataclass(frozen=True)
class NLPConfig:
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD
    gemini_batch_size: int = _DEFAULT_GEMINI_BATCH_SIZE


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
    )
