from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CommentDTO:
    comment_id: str
    video_id: str
    channel_id: str
    text_original: str
    is_reply: bool
    crawl_type: str
    crawled_at: datetime
    parent_comment_id: Optional[str] = None
    author_channel_id: Optional[str] = None
    author_display_name: Optional[str] = None
    text_display: Optional[str] = None
    like_count: int = 0
    reply_count: int = 0
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def gcs_partition_date(self) -> str:
        return self.crawled_at.strftime("%Y/%m/%d")

    def to_dict(self) -> dict:
        return {
            "comment_id": self.comment_id,
            "video_id": self.video_id,
            "channel_id": self.channel_id,
            "parent_comment_id": self.parent_comment_id,
            "author_channel_id": self.author_channel_id,
            "author_display_name": self.author_display_name,
            "text_original": self.text_original,
            "text_display": self.text_display,
            "like_count": self.like_count,
            "reply_count": self.reply_count,
            "is_reply": self.is_reply,
            "crawl_type": self.crawl_type,
            "published_at": (
                self.published_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.published_at else None
            ),
            "updated_at": (
                self.updated_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.updated_at else None
            ),
            "gcs_partition_date": self.gcs_partition_date,
            "crawled_at": self.crawled_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }