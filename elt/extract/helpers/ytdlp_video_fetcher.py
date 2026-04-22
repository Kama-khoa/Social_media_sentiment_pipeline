from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    _FILTER_CLUSTER = "_uncategorized"

    def __init__(self, keywords: list[KeywordDTO], max_workers: int = 8) -> None:
        self._filter_keywords = [
            kw for kw in keywords
            if kw.search_cluster == self._FILTER_CLUSTER
        ]
        self._filter_texts = [kw.keyword_text.lower() for kw in self._filter_keywords]
        self._max_workers = max_workers

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

    def filter_by_keywords(self, videos: list[dict]) -> list[dict]:
        matched: list[dict] = []
        for video in videos:
            title_lower = video.get("title", "").lower()
            desc_lower = video.get("description", "").lower()
            for idx, kw_text in enumerate(self._filter_texts):
                if kw_text in title_lower or kw_text in desc_lower:
                    video["_matched_keyword"] = self._filter_keywords[idx].keyword_text
                    matched.append(video)
                    break
        return matched

    def enrich_batch(self, entries: list[dict], max_workers: int | None = None) -> list[dict]:
        workers = max_workers or self._max_workers
        enriched_map: dict[str, dict] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_id = {
                pool.submit(self._enrich_video, entry["id"]): entry["id"]
                for entry in entries
            }
            for future in as_completed(future_to_id):
                video_id = future_to_id[future]
                try:
                    enriched_map[video_id] = future.result()
                except Exception:
                    logger.warning("enrich_batch: failed for %s", video_id)
                    enriched_map[video_id] = {}

        merged: list[dict] = []
        for entry in entries:
            video_id = entry["id"]
            enriched = enriched_map.get(video_id, {})
            combined = {**entry, **{k: v for k, v in enriched.items() if v is not None}}
            merged.append(combined)

        logger.info("enrich_batch: %d/%d videos enriched", len(merged), len(entries))
        return merged

    def build_video_dtos(
        self,
        enriched_entries: list[dict],
        channel_id: str,
        search_mode: str = "MODE0",
    ) -> list[VideoDTO]:
        now = datetime.now(timezone.utc)
        dtos: list[VideoDTO] = []

        for entry in enriched_entries:
            published_at = self._parse_published_at(entry)
            if published_at is None:
                continue

            video_id = entry.get("id", "")
            if not video_id:
                continue

            dtos.append(VideoDTO(
                video_id=video_id,
                channel_id=entry.get("channel_id") or channel_id,
                title=entry.get("title", ""),
                published_at=published_at,
                search_mode=search_mode,
                crawled_at=now,
                description=entry.get("description"),
                view_count=entry.get("view_count"),
                like_count=entry.get("like_count"),
                comment_count=entry.get("comment_count"),
                duration_seconds=entry.get("duration"),
                tags=entry.get("tags") or [],
                thumbnail_url=entry.get("thumbnail"),
                keyword_matched=entry.get("_matched_keyword"),
            ))

        return dtos

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

    @staticmethod
    def _parse_published_at(entry: dict) -> datetime | None:
        published_at = entry.get("published_at")
        if isinstance(published_at, datetime):
            if published_at.tzinfo is None:
                return published_at.replace(tzinfo=timezone.utc)
            return published_at

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