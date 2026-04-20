from __future__ import annotations

import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build

from elt.datacontext.models.video_dto import VideoDTO

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50
_SKIP_CLUSTERS = {"_uncategorized"}


class YouTubeApiClient:

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._service = build("youtube", "v3", developerKey=api_key)

    def search_videos(
        self,
        keyword: str,
        max_results: int = 10,
        search_cluster: str | None = None,
    ) -> list[tuple[str, str]]:
        if search_cluster and search_cluster in _SKIP_CLUSTERS:
            logger.debug("Skipping keyword=%s (cluster=%s)", keyword, search_cluster)
            return []

        try:
            response = (
                self._service
                .search()
                .list(
                    q=keyword,
                    part="snippet",
                    type="video",
                    maxResults=min(max_results, 50),
                    relevanceLanguage="vi",
                    order="relevance",
                )
                .execute()
            )
        except Exception:
            logger.exception("search.list failed for keyword=%s", keyword)
            return []

        pairs: list[tuple[str, str]] = []
        for item in response.get("items", []):
            video_id = item["id"].get("videoId")
            channel_id = item["snippet"].get("channelId")
            if video_id and channel_id:
                pairs.append((video_id, channel_id))
        return pairs

    def get_video_details(self, video_ids: list[str]) -> list[VideoDTO]:
        if not video_ids:
            return []

        all_dtos: list[VideoDTO] = []
        for i in range(0, len(video_ids), _BATCH_SIZE):
            batch = video_ids[i : i + _BATCH_SIZE]
            dtos = self._fetch_batch(batch)
            all_dtos.extend(dtos)
        return all_dtos

    def _fetch_batch(self, video_ids: list[str]) -> list[VideoDTO]:
        try:
            response = (
                self._service
                .videos()
                .list(
                    id=",".join(video_ids),
                    part="snippet,statistics,contentDetails",
                )
                .execute()
            )
        except Exception:
            logger.exception("videos.list failed for %d ids", len(video_ids))
            return []

        return [
            self._build_video_dto(item)
            for item in response.get("items", [])
            if item.get("id")
        ]

    def _build_video_dto(self, item: dict) -> VideoDTO:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        now = datetime.now(timezone.utc)

        published_at = self._parse_iso(snippet.get("publishedAt"))
        if published_at is None:
            published_at = now

        return VideoDTO(
            video_id=item["id"],
            channel_id=snippet.get("channelId", ""),
            title=snippet.get("title", ""),
            published_at=published_at,
            search_mode="MODE2",
            crawled_at=now,
            description=snippet.get("description"),
            view_count=self._safe_int(stats.get("viewCount")),
            like_count=self._safe_int(stats.get("likeCount")),
            comment_count=self._safe_int(stats.get("commentCount")),
            duration_seconds=self._parse_duration(content.get("duration")),
            tags=snippet.get("tags") or [],
            thumbnail_url=self._best_thumbnail(snippet.get("thumbnails", {})),
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
    def _safe_int(val) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_duration(raw: str | None) -> int | None:
        if not raw or not raw.startswith("PT"):
            return None
        raw = raw[2:]
        total = 0
        current = ""
        for ch in raw:
            if ch.isdigit():
                current += ch
            elif ch == "H":
                total += int(current) * 3600
                current = ""
            elif ch == "M":
                total += int(current) * 60
                current = ""
            elif ch == "S":
                total += int(current)
                current = ""
        return total if total > 0 else None

    @staticmethod
    def _best_thumbnail(thumbnails: dict) -> str | None:
        for key in ("maxres", "high", "medium", "default"):
            thumb = thumbnails.get(key)
            if thumb and thumb.get("url"):
                return thumb["url"]
        return None