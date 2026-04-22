from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from elt.config import PipelineConfig
from elt.datacontext.gcs_client import GCSClient
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.comment_downloader import CommentDownloader, ProxyConfig
from elt.extract.helpers.comment_worker import CommentWorker
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.quota_repository import QuotaRepository

logger = logging.getLogger(__name__)


class CommentExtractor:

    def __init__(
        self,
        config: PipelineConfig,
        crawl_state_repo: CrawlStateRepository,
        quota_repo: QuotaRepository,
        gcs_client: GCSClient,
        proxy_config: Optional[ProxyConfig] = None,
    ) -> None:
        self._config = config
        self._crawl_state_repo = crawl_state_repo
        self._quota_repo = quota_repo
        self._gcs_client = gcs_client
        self._downloader = CommentDownloader(proxy_config)
        self._worker = CommentWorker(
            downloader=self._downloader,
            crawl_state_repo=self._crawl_state_repo,
            gcs_client=self._gcs_client,
            max_comments=config.crawl.max_comments_per_video,
            new_video_min_age_days=config.crawl.new_video_min_age_days,
        )

    def crawl_batch(self, videos: list[VideoDTO]) -> tuple[int, list[VideoDTO]]:
        success_count = 0
        failed: list[VideoDTO] = []
        delay = self._config.comment_downloader.request_delay_seconds

        for video in videos:
            ok = self._worker.process(video)
            if ok:
                success_count += 1
            else:
                failed.append(video)

            if delay > 0:
                time.sleep(delay)

        return success_count, failed

    def crawl_batch_with_retry(
        self,
        videos: list[VideoDTO],
        max_retries: int = 2,
    ) -> dict:
        total_crawled = 0
        total_retried = 0

        crawled, failed = self.crawl_batch(videos)
        total_crawled += crawled

        for attempt in range(1, max_retries + 1):
            if not failed:
                break
            logger.info(
                "Comment retry attempt %d: %d videos",
                attempt, len(failed),
            )
            total_retried += len(failed)
            crawled, failed = self.crawl_batch(failed)
            total_crawled += crawled

        for video in failed:
            self._crawl_state_repo.mark_video_skipped(video.video_id)

        logger.info(
            "crawl_batch_with_retry: %d crawled, %d retried, %d failed",
            total_crawled, total_retried, len(failed),
        )

        return {
            "videos_crawled": total_crawled,
            "videos_retried": total_retried,
            "videos_failed": len(failed),
        }

    def run_backlog(self, dag_run_id: str) -> dict:
        t0 = time.monotonic()

        raw_videos = self._crawl_state_repo.get_videos_to_crawl()
        if not raw_videos:
            logger.info("Backlog: no videos to crawl")
            return {"videos_crawled": 0, "videos_failed": 0, "elapsed_seconds": 0}

        dtos = self._build_dtos_from_crawl_state(raw_videos)
        logger.info("Backlog: %d videos eligible", len(dtos))

        stats = self.crawl_batch_with_retry(dtos, max_retries=2)

        elapsed = time.monotonic() - t0
        self._quota_repo.log_operation(
            operation_type="comment_extraction_backlog",
            bucket="comment_downloader",
            units_used=0,
            dag_run_id=dag_run_id,
            videos_processed=stats["videos_crawled"],
            comments_collected=0,
            execution_time_seconds=elapsed,
        )

        stats["elapsed_seconds"] = round(elapsed, 2)
        return stats

    @staticmethod
    def _build_dtos_from_crawl_state(raw_videos: list[dict]) -> list[VideoDTO]:
        now = datetime.now(timezone.utc)
        dtos: list[VideoDTO] = []
        for row in raw_videos:
            published_at = row.get("published_at")
            if published_at is None:
                continue
            if isinstance(published_at, datetime):
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            else:
                continue

            dtos.append(VideoDTO(
                video_id=row["video_id"],
                channel_id=row["channel_id"],
                title="",
                published_at=published_at,
                search_mode="BACKLOG",
                crawled_at=now,
                comment_count=row.get("comment_count"),
            ))
        return dtos