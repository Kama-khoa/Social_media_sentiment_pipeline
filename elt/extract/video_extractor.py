from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from elt.config import PipelineConfig
from elt.datacontext.gcs_client import GCSClient
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.youtube_api_client import YouTubeApiClient
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpVideoFetcher
from elt.quota_budget import QuotaBucket, QuotaBudget
from elt.repositories.channel_repository import ChannelRepository
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.keyword_repository import KeywordRepository
from elt.repositories.quota_repository import QuotaRepository

if TYPE_CHECKING:
    from elt.extract.comment_extractor import CommentExtractor

logger = logging.getLogger(__name__)

_SEARCH_UNITS_PER_CALL = 100


def _chunks(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


class VideoExtractor:

    def __init__(
        self,
        config: PipelineConfig,
        channel_repo: ChannelRepository,
        keyword_repo: KeywordRepository,
        crawl_state_repo: CrawlStateRepository,
        quota_repo: QuotaRepository,
        gcs_client: GCSClient,
    ) -> None:
        self._config = config
        self._channel_repo = channel_repo
        self._keyword_repo = keyword_repo
        self._crawl_state_repo = crawl_state_repo
        self._quota_repo = quota_repo
        self._gcs_client = gcs_client
        self._api_client = YouTubeApiClient(config.youtube_api_key)

    def run_daily(
        self,
        execution_date: str,
        dag_run_id: str,
        budget: QuotaBudget,
        comment_extractor: Optional[CommentExtractor] = None,
    ) -> dict:
        t0 = time.monotonic()
        channels = self._channel_repo.get_active_channels()
        keywords = self._keyword_repo.get_active_keywords()
        fetcher = YtdlpVideoFetcher(keywords, self._config.crawl.enrich_max_workers)

        lookback_days = self._config.crawl.daily_scan_lookback_days
        published_after = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        max_results = self._config.crawl.daily_scan_max_results

        all_raw: list[dict] = []
        channels_scanned = 0

        for ch in channels:
            if not budget.can_consume(QuotaBucket.SEARCH, _SEARCH_UNITS_PER_CALL):
                logger.warning("Phase A: quota exhausted after %d channels", channels_scanned)
                break

            raw = self._api_client.search_channel_recent(
                ch.channel_id, published_after, max_results,
            )
            budget.consume(QuotaBucket.SEARCH, _SEARCH_UNITS_PER_CALL)
            channels_scanned += 1

            for entry in raw:
                entry["channel_id"] = entry.get("channel_id") or ch.channel_id
            all_raw.extend(raw)

        logger.info("Phase A: %d raw videos from %d channels", len(all_raw), channels_scanned)

        matched = fetcher.filter_by_keywords(all_raw)
        logger.info("Phase A: %d videos matched keywords", len(matched))

        existing_ids = self._crawl_state_repo.get_all_video_ids()
        new_videos = [v for v in matched if v["id"] not in existing_ids]
        logger.info("Phase A: %d new videos after dedupe", len(new_videos))

        total_saved = 0
        comment_stats: dict = {}

        if new_videos:
            enriched = fetcher.enrich_batch(new_videos)
            dtos = fetcher.build_video_dtos(enriched, channel_id="", search_mode="DAILY")

            if dtos:
                try:
                    self._upload_to_gcs(dtos, execution_date)
                    self._save_to_crawl_state(dtos)
                except Exception as e:
                    logger.error("Phase A: save failed: %s", e)
                    raise

                total_saved = len(dtos)

                if comment_extractor:
                    comment_stats = comment_extractor.crawl_batch_with_retry(dtos, max_retries=2)

        elapsed = time.monotonic() - t0
        self._quota_repo.log_operation(
            operation_type="video_extraction_daily",
            bucket=QuotaBucket.SEARCH.value,
            units_used=channels_scanned * _SEARCH_UNITS_PER_CALL,
            dag_run_id=dag_run_id,
            videos_processed=total_saved,
            execution_time_seconds=elapsed,
        )

        return {
            "channels_scanned": channels_scanned,
            "raw_found": len(all_raw),
            "keyword_matched": len(matched),
            "new_saved": total_saved,
            "comment_stats": comment_stats,
            "elapsed_seconds": round(elapsed, 2),
        }

    def run_historical(
        self,
        execution_date: str,
        dag_run_id: str,
        budget: QuotaBudget,
        comment_extractor: Optional[CommentExtractor] = None,
    ) -> dict:
        t0 = time.monotonic()
        limit = self._config.crawl.historical_scan_channels_per_day
        channels = self._channel_repo.get_unscanned_channels(limit=limit)

        if not channels:
            logger.info("Phase B: all channels already scanned, skipping")
            return {"channels_scanned": 0, "total_saved": 0, "elapsed_seconds": 0}

        keywords = self._keyword_repo.get_active_keywords()
        fetcher = YtdlpVideoFetcher(keywords, self._config.crawl.enrich_max_workers)
        batch_size = self._config.crawl.video_batch_size

        total_saved = 0
        channels_done = 0

        for ch in channels:
            url = ch.channel_url or f"https://www.youtube.com/{ch.channel_handle}"
            logger.info("Phase B: scanning channel %s (%s)", ch.channel_name, url)

            raw = fetcher.fetch_channel_videos(url)
            matched = fetcher.filter_by_keywords(raw)
            logger.info(
                "Phase B: channel %s — %d total, %d matched",
                ch.channel_name, len(raw), len(matched),
            )

            existing_ids = self._crawl_state_repo.get_existing_video_ids(ch.channel_id)
            remaining = [v for v in matched if v["id"] not in existing_ids]
            logger.info(
                "Phase B: channel %s — %d remaining after resume skip",
                ch.channel_name, len(remaining),
            )

            channel_comment_fails: list[VideoDTO] = []
            batch_num = 0
            total_batches = (len(remaining) + batch_size - 1) // batch_size if remaining else 0

            for batch_entries in _chunks(remaining, batch_size):
                batch_num += 1
                enriched = fetcher.enrich_batch(batch_entries)
                dtos = fetcher.build_video_dtos(enriched, ch.channel_id, search_mode="MODE0")

                if not dtos:
                    continue

                try:
                    self._upload_to_gcs(dtos, execution_date)
                    self._save_to_crawl_state(dtos)
                except Exception as e:
                    logger.error(
                        "Phase B: save failed for channel %s batch %d/%d: %s",
                        ch.channel_name, batch_num, total_batches, e,
                    )
                    raise

                total_saved += len(dtos)
                logger.info(
                    "Phase B: channel %s — batch %d/%d saved (%d videos, %d total)",
                    ch.channel_name, batch_num, total_batches, len(dtos), total_saved,
                )

                if comment_extractor:
                    _, fails = comment_extractor.crawl_batch(dtos)
                    channel_comment_fails.extend(fails)

            if comment_extractor and channel_comment_fails:
                logger.info(
                    "Phase B: retrying %d failed comments for channel %s",
                    len(channel_comment_fails), ch.channel_name,
                )
                comment_extractor.crawl_batch_with_retry(channel_comment_fails, max_retries=2)

            self._channel_repo.mark_historically_scanned(ch.channel_id)
            channels_done += 1
            logger.info("Phase B: channel %s marked as scanned", ch.channel_name)

        elapsed = time.monotonic() - t0
        self._quota_repo.log_operation(
            operation_type="video_extraction_historical",
            bucket=QuotaBucket.SEARCH.value,
            units_used=0,
            dag_run_id=dag_run_id,
            videos_processed=total_saved,
            execution_time_seconds=elapsed,
        )

        return {
            "channels_scanned": channels_done,
            "total_saved": total_saved,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _save_to_crawl_state(self, videos: list[VideoDTO]) -> None:
        self._crawl_state_repo.bulk_upsert_from_video_dtos(videos)
        logger.info("Saved %d videos to crawl_state", len(videos))

    def _upload_to_gcs(self, videos: list[VideoDTO], execution_date: str) -> None:
        now = datetime.now(timezone.utc)
        gcs_path = GCSClient.build_videos_path(now)
        payload = [v.to_dict() for v in videos]
        uri = self._gcs_client.upload_json(gcs_path, payload)
        logger.info("Uploaded %d videos to %s", len(videos), uri)