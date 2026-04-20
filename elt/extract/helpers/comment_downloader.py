from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from youtube_comment_downloader import YoutubeCommentDownloader

from elt.datacontext.models.comment_dto import CommentDTO

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str

    def to_proxy_url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"


class CommentDownloader:

    def __init__(self, proxy_config: Optional[ProxyConfig] = None) -> None:
        self._proxy_config = proxy_config

    def download(self, video_id: str, max_comments: int = 500) -> list[dict]:
        downloader = YoutubeCommentDownloader()
        proxy = self._proxy_config.to_proxy_url() if self._proxy_config else None

        try:
            generator = downloader.get_comments_from_url(
                f"https://www.youtube.com/watch?v={video_id}",
                sort_by=0,
            )
            comments = list(itertools.islice(generator, max_comments))
        except Exception:
            logger.exception("Comment download failed for video_id=%s", video_id)
            return []

        return comments

    def to_comment_dtos(
        self,
        raw_comments: list[dict],
        video_id: str,
        channel_id: str,
    ) -> list[CommentDTO]:
        now = datetime.now(timezone.utc)
        dtos: list[CommentDTO] = []
        for raw in raw_comments:
            cid = raw.get("cid")
            text = raw.get("text")
            if not cid or not text:
                continue

            is_reply = bool(raw.get("reply", False))
            parent_id = None
            if is_reply and "." in cid:
                parent_id = cid.split(".")[0]

            published_at = self._parse_time(raw.get("time_parsed"))

            dtos.append(CommentDTO(
                comment_id=cid,
                video_id=video_id,
                channel_id=channel_id,
                text_original=text,
                is_reply=is_reply,
                crawl_type="full",
                crawled_at=now,
                parent_comment_id=parent_id,
                author_channel_id=raw.get("channel"),
                author_display_name=raw.get("author"),
                text_display=text,
                like_count=self._safe_int(raw.get("votes", 0)),
                reply_count=self._safe_int(raw.get("replies", 0)),
                published_at=published_at,
                updated_at=published_at,
            ))
        return dtos

    @staticmethod
    def _parse_time(val) -> datetime | None:
        if val is None:
            return None
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            return None

    @staticmethod
    def _safe_int(val) -> int:
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0