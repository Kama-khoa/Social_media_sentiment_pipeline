from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class VideoDTO:
    video_id: str
    channel_id: str
    title: str
    published_at: datetime
    search_mode: str
    crawled_at: datetime
    description: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    tags: list[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    keyword_matched: Optional[str] = None

    @property
    def gcs_partition_date(self) -> str:
        return self.crawled_at.strftime("%Y/%m/%d")

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "channel_id": self.channel_id,
            "title": self.title,
            "description": self.description,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "duration_seconds": self.duration_seconds,
            "tags": self.tags,
            "thumbnail_url": self.thumbnail_url,
            "published_at": self.published_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "search_mode": self.search_mode,
            "keyword_matched": self.keyword_matched,
            "gcs_partition_date": self.gcs_partition_date,
            "crawled_at": self.crawled_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }