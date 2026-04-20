from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import yt_dlp  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from yt_dlp import YoutubeDL

from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO

logger = logging.getLogger(__name__)


def _make_ydl(**kwargs: Any) -> YoutubeDL:
    return yt_dlp.YoutubeDL(kwargs)  # type: ignore[arg-type]


class YtdlpVideoFetcher:

    def __init__(self, keywords: list[KeywordDTO]) -> None:
        self._keywords = keywords
        self._keyword_texts = [kw.keyword_text.lower() for kw in keywords]

    def fetch_channel_videos(self, channel_url: str) -> list[dict]:
        url = f"{channel_url}/videos"
        try:
            with _make_ydl(
                quiet=True,
                no_warnings=True,
                extract_flat=True,
                skip_download=True,
                ignoreerrors=True,
            ) as ydl:
                result = ydl.extract_info(url, download=False)
        except Exception:
            logger.exception("yt-dlp failed for %s", channel_url)
            return []

        if result is None:
            return []

        entries = result.get("entries") or []
        videos = []
        for entry in entries:
            if entry is None:
                continue
            videos.append({
                "id": entry.get("id", ""),
                "title": entry.get("title", ""),
                "description": entry.get("description") or "",
                "upload_date": entry.get("upload_date"),
                "view_count": entry.get("view_count"),
                "duration": entry.get("duration"),
                "thumbnail": entry.get("thumbnail"),
            })
        return videos

    def _enrich_video(self, video_id: str) -> dict[str, Any]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with _make_ydl(
                quiet=True,
                no_warnings=True,
                extract_flat=False,
                skip_download=True,
                ignoreerrors=True,
            ) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            logger.warning("yt-dlp enrich failed for %s", video_id)
            return {}
        return dict(info) if info else {}

    def filter_by_keywords(self, videos: list[dict]) -> list[dict]:
        matched: list[dict] = []
        for video in videos:
            title_lower = video.get("title", "").lower()
            desc_lower = video.get("description", "").lower()
            for idx, kw_text in enumerate(self._keyword_texts):
                if kw_text in title_lower or kw_text in desc_lower:
                    video["_matched_keyword"] = self._keywords[idx].keyword_text
                    matched.append(video)
                    break
        return matched

    def to_video_dtos(
        self,
        videos: list[dict],
        channel_id: str,
    ) -> list[VideoDTO]:
        now = datetime.now(timezone.utc)
        dtos: list[VideoDTO] = []
        for v in videos:
            enriched = self._enrich_video(v["id"])
            merged = {**v, **{k: val for k, val in enriched.items() if val is not None}}

            published_at = self._parse_published_at(merged)
            if published_at is None:
                continue

            dtos.append(VideoDTO(
                video_id=v["id"],
                channel_id=channel_id,
                title=merged.get("title") or v.get("title", ""),
                published_at=published_at,
                search_mode="MODE0",
                crawled_at=now,
                description=merged.get("description"),
                view_count=merged.get("view_count"),
                like_count=merged.get("like_count"),
                comment_count=merged.get("comment_count"),
                duration_seconds=merged.get("duration"),
                tags=merged.get("tags") or [],
                thumbnail_url=merged.get("thumbnail"),
                keyword_matched=v.get("_matched_keyword"),
            ))
        return dtos

    @staticmethod
    def _parse_published_at(entry: dict) -> datetime | None:
        timestamp = entry.get("timestamp")
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (OSError, OverflowError, ValueError):
                pass
        upload_date = entry.get("upload_date")
        if upload_date:
            try:
                return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return None
