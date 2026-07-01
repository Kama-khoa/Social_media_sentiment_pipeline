from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from elt.config import PipelineConfig


class QuotaBucket(str, Enum):
    SEARCH = "search_videos"
    CHANNEL_SEED = "channel_seed"
    COMMENT_THREADS = "youtube_api_comments"


@dataclass
class QuotaBudget:
    total: int
    safety_buffer: int
    _remaining: dict[QuotaBucket, int] = field(default_factory=dict, repr=False)

    @classmethod
    def from_config(
        cls,
        config: "PipelineConfig",
        already_used_by_bucket: dict[str, int],
    ) -> "QuotaBudget":
        allocations = {
            QuotaBucket.SEARCH: config.quota.bucket_search,
            QuotaBucket.CHANNEL_SEED: config.quota.bucket_channel_seed,
            QuotaBucket.COMMENT_THREADS: config.api_comment_backfill.daily_quota_units,
        }
        remaining = {
            bucket: max(0, alloc - already_used_by_bucket.get(bucket.value, 0))
            for bucket, alloc in allocations.items()
        }
        budget = cls(
            total=config.quota.daily_budget,
            safety_buffer=config.quota.safety_buffer,
        )
        budget._remaining = remaining
        return budget

    def remaining(self, bucket: QuotaBucket) -> int:
        return self._remaining.get(bucket, 0)

    def can_consume(self, bucket: QuotaBucket, units: int = 1) -> bool:
        return self._remaining.get(bucket, 0) >= units

    def consume(self, bucket: QuotaBucket, units: int) -> None:
        current = self._remaining.get(bucket, 0)
        if units > current:
            raise InsufficientQuotaError(bucket, units, current)
        self._remaining[bucket] = current - units

    def try_consume(self, bucket: QuotaBucket, units: int) -> bool:
        if not self.can_consume(bucket, units):
            return False
        self.consume(bucket, units)
        return True

    def summary(self) -> dict[str, int]:
        return {b.value: r for b, r in self._remaining.items()}

    def __str__(self) -> str:
        parts = ", ".join(f"{b.value}={r}" for b, r in self._remaining.items())
        return f"QuotaBudget({parts})"


class InsufficientQuotaError(Exception):
    def __init__(self, bucket: QuotaBucket, needed: int, available: int) -> None:
        super().__init__(
            f"Bucket '{bucket.value}': needed {needed}, available {available}"
        )
        self.bucket = bucket
        self.needed = needed
        self.available = available
