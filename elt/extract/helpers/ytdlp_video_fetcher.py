from __future__ import annotations

import logging
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import yt_dlp  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from yt_dlp import YoutubeDL

from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO

logger = logging.getLogger(__name__)

_BOT_DETECTION_PHRASES = [
    "Sign in to confirm",
    "confirm you're not a bot",
]

_MAX_BACKOFF_RETRIES = 3
_BACKOFF_BASE_SECONDS = 30
_FAILURE_RATE_THRESHOLD = 0.5


class BotDetectedError(Exception):
    pass


def _make_ydl(cookies_path: str | None = None, proxy: str | None = None, **kwargs: Any) -> YoutubeDL:
    if cookies_path:
        kwargs["cookiefile"] = cookies_path
    if proxy:
        kwargs["proxy"] = proxy
    return yt_dlp.YoutubeDL(kwargs)  # type: ignore[arg-type]


class YtdlpVideoFetcher:

    _FILTER_CLUSTER = "_uncategorized"

    def __init__(
        self,
        keywords: list[KeywordDTO],
        max_workers: int = 8,
        cookies_path: str | None = None,
        proxy: str | None = None,
    ) -> None:
        self._filter_keywords = [
            kw for kw in keywords
            if kw.search_cluster == self._FILTER_CLUSTER
        ]
        self._filter_texts = [kw.keyword_text.lower() for kw in self._filter_keywords]
        self._max_workers = max_workers
        self._cookies_path = cookies_path
        self._proxy = proxy

    def fetch_channel_videos(self, channel_url: str) -> list[dict]:
        url = f"{channel_url}/videos"
        # Create a temporary copy of the cookie file to prevent yt-dlp from overwriting it
        temp_cookie_path = None
        if self._cookies_path:
            try:
                import os
                fd, temp_cookie_path = tempfile.mkstemp(suffix=".txt")
                os.close(fd)
                shutil.copy2(self._cookies_path, temp_cookie_path)
            except Exception:
                pass

        try:
            with _make_ydl(
                cookies_path=temp_cookie_path or self._cookies_path,
                proxy=self._proxy,
                # quiet=True,
                # no_warnings=True,
                extract_flat=True,
                skip_download=True,
                ignoreerrors=True,
                extractor_args={'youtubetab': ['skip=authcheck']},
            ) as ydl:
                result = ydl.extract_info(url, download=False)
        except Exception:
            logger.exception("yt-dlp failed for %s", channel_url)
            return []
        finally:
            if temp_cookie_path:
                try:
                    import os
                    os.remove(temp_cookie_path)
                except Exception:
                    pass

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
        remaining = list(entries)

        for attempt in range(_MAX_BACKOFF_RETRIES + 1):
            batch_results = self._enrich_parallel(remaining, workers)

            succeeded: list[dict] = []
            failed: list[dict] = []

            for entry in remaining:
                video_id = entry["id"]
                result = batch_results.get(video_id, {})
                if result:
                    enriched_map[video_id] = result
                    succeeded.append(entry)
                else:
                    failed.append(entry)

            if not failed:
                break

            failure_rate = len(failed) / len(remaining) if remaining else 0

            if failure_rate < _FAILURE_RATE_THRESHOLD:
                for entry in failed:
                    enriched_map.setdefault(entry["id"], {})
                break

            if attempt < _MAX_BACKOFF_RETRIES:
                wait = _BACKOFF_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "enrich_batch: %.0f%% failed (%d/%d), backoff %ds before retry %d/%d",
                    failure_rate * 100, len(failed), len(remaining),
                    wait, attempt + 1, _MAX_BACKOFF_RETRIES,
                )
                time.sleep(wait)
                remaining = failed
            else:
                logger.error(
                    "enrich_batch: giving up after %d retries, %d videos unenriched",
                    _MAX_BACKOFF_RETRIES, len(failed),
                )
                for entry in failed:
                    enriched_map.setdefault(entry["id"], {})

        merged: list[dict] = []
        enriched_count = 0
        for entry in entries:
            video_id = entry["id"]
            enriched = enriched_map.get(video_id, {})
            combined = {**entry, **{k: v for k, v in enriched.items() if v is not None}}
            merged.append(combined)
            if enriched:
                enriched_count += 1

        logger.info("enrich_batch: %d/%d videos enriched", enriched_count, len(entries))
        return merged

    def _enrich_parallel(self, entries: list[dict], workers: int) -> dict[str, dict]:
        # Process sequentially with a single yt-dlp instance and randomized sleeps
        # to avoid triggering YouTube's aggressive anti-bot rate limits.
        results: dict[str, dict] = {}
        
        temp_cookie_path = None
        if self._cookies_path:
            try:
                import os
                fd, temp_cookie_path = tempfile.mkstemp(suffix=".txt")
                os.close(fd)
                shutil.copy2(self._cookies_path, temp_cookie_path)
            except Exception:
                pass

        try:
            with _make_ydl(
                cookies_path=temp_cookie_path or self._cookies_path,
                proxy=self._proxy,
                quiet=True,
                no_warnings=True,
                extract_flat=False,
                skip_download=True,
                ignoreerrors=True,
                sleep_interval_requests=3,
                max_sleep_interval_requests=7,
            ) as ydl:
                for entry in entries:
                    video_id = entry["id"]
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    try:
                        info = ydl.extract_info(url, download=False)
                        results[video_id] = dict(info) if info else {}
                    except Exception as exc:
                        msg = str(exc)
                        if any(phrase in msg for phrase in _BOT_DETECTION_PHRASES):
                            logger.warning("Bot detected for %s", video_id)
                        else:
                            logger.warning("enrich failed for %s", video_id)
                        results[video_id] = {}
        finally:
            if temp_cookie_path:
                try:
                    import os
                    os.remove(temp_cookie_path)
                except Exception:
                    pass

        return results

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
        temp_cookie_path = None
        if self._cookies_path:
            try:
                import os
                fd, temp_cookie_path = tempfile.mkstemp(suffix=".txt")
                os.close(fd)
                shutil.copy2(self._cookies_path, temp_cookie_path)
            except Exception:
                pass

        try:
            with _make_ydl(
                cookies_path=temp_cookie_path or self._cookies_path,
                proxy=self._proxy,
                quiet=True,
                no_warnings=True,
                extract_flat=False,
                skip_download=True,
                ignoreerrors=False,
                format="worst",
            ) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            msg = str(exc)
            if any(phrase in msg for phrase in _BOT_DETECTION_PHRASES):
                raise BotDetectedError(video_id) from exc
            logger.warning("yt-dlp enrich failed for %s", video_id)
            return {}
        finally:
            if temp_cookie_path:
                try:
                    import os
                    os.remove(temp_cookie_path)
                except Exception:
                    pass
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