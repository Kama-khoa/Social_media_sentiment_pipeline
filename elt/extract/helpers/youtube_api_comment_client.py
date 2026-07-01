from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from googleapiclient.discovery import build

from elt.datacontext.models.comment_dto import CommentDTO


@dataclass
class CommentPage:
    comments: list[CommentDTO]
    next_page_token: str | None
    quota_units_used: int


class YouTubeApiCommentClient:
    def __init__(self, api_key: str) -> None:
        self._service = build("youtube", "v3", developerKey=api_key)

    def fetch_top_level_page(
        self,
        video_id: str,
        channel_id: str,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> CommentPage:
        request = (
            self._service
            .commentThreads()
            .list(
                videoId=video_id,
                part="snippet",
                maxResults=min(max_results, 100),
                order="time",
                textFormat="plainText",
                pageToken=page_token,
            )
        )
        response = request.execute()

        now = datetime.now(timezone.utc)
        comments = [
            dto
            for item in response.get("items", [])
            if (dto := self._item_to_dto(item, video_id, channel_id, now)) is not None
        ]
        return CommentPage(
            comments=comments,
            next_page_token=response.get("nextPageToken"),
            quota_units_used=1,
        )

    def _item_to_dto(
        self,
        item: dict,
        video_id: str,
        channel_id: str,
        crawled_at: datetime,
    ) -> CommentDTO | None:
        comment = item.get("snippet", {}).get("topLevelComment", {})
        comment_id = comment.get("id") or item.get("id")
        snippet = comment.get("snippet", {})
        text = snippet.get("textOriginal") or snippet.get("textDisplay")
        if not comment_id or not text:
            return None

        published_at = self._parse_iso(snippet.get("publishedAt"))
        updated_at = self._parse_iso(snippet.get("updatedAt")) or published_at
        author_channel = snippet.get("authorChannelId")
        if isinstance(author_channel, dict):
            author_channel_id = author_channel.get("value")
        else:
            author_channel_id = author_channel
        return CommentDTO(
            comment_id=comment_id,
            video_id=video_id,
            channel_id=snippet.get("channelId") or channel_id,
            text_original=text,
            is_reply=False,
            crawl_type="api_backfill",
            crawled_at=crawled_at,
            parent_comment_id=None,
            author_channel_id=author_channel_id,
            author_display_name=snippet.get("authorDisplayName"),
            text_display=snippet.get("textDisplay") or text,
            like_count=self._safe_int(snippet.get("likeCount")),
            reply_count=self._safe_int(item.get("snippet", {}).get("totalReplyCount")),
            published_at=published_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _parse_iso(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _safe_int(value) -> int:
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
