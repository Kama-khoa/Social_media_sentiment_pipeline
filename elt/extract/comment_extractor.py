from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from elt.config import PipelineConfig
from elt.datacontext.gcs_client import GCSClient
from elt.datacontext.models.comment_dto import CommentDTO
from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.base_extractor import BaseExtractor
from elt.extract.helpers.comment_downloader import CommentDownloader, ProxyConfig
from elt.extract.helpers.rss_feed_reader import RssFeedReader
from elt.extract.helpers.youtube_api_client import YouTubeApiClient
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpVideoFetcher
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.quota_repository import QuotaRepository

logger = logging.getLogger(__name__)


class CommentExtractor(BaseExtractor):

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

    def run(self, dag_run_id: str) -> dict:
        t0 = time.monotonic()
        videos = self._get_videos_to_crawl()
        eligible = self._apply_maturity_filter(videos)

        total_comments = 0
        videos_crawled = 0
        videos_skipped = 0

        for video in eligible:
            video_id = video["video_id"]
            channel_id = video["channel_id"]

            comments = self._crawl_video_comments(video)
            if not comments:
                self._crawl_state_repo.mark_video_skipped(video_id)
                videos_skipped += 1
                continue

            self._upload_to_gcs(comments, video_id)
            self._update_crawl_state(video_id, len(comments))

            total_comments += len(comments)
            videos_crawled += 1

            delay = self._config.comment_downloader.request_delay_seconds
            if delay > 0:
                time.sleep(delay)

        elapsed = time.monotonic() - t0
        self._quota_repo.log_operation(
            operation_type="comment_extraction",
            bucket="comment_downloader",
            units_used=0,
            dag_run_id=dag_run_id,
            videos_processed=videos_crawled,
            comments_collected=total_comments,
            execution_time_seconds=elapsed,
        )

        logger.info(
            "Comment extraction done: %d videos crawled, %d skipped, %d comments total",
            videos_crawled,
            videos_skipped,
            total_comments,
        )

        return {
            "videos_crawled": videos_crawled,
            "videos_skipped": videos_skipped,
            "total_comments": total_comments,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _get_videos_to_crawl(self) -> list[dict]:
        return self._crawl_state_repo.get_videos_to_crawl()

    def _apply_maturity_filter(self, videos: list[dict]) -> list[dict]:
        min_age = self._config.crawl.new_video_min_age_days
        now = datetime.now(timezone.utc)
        eligible: list[dict] = []

        for v in videos:
            stage = v.get("maturity_stage", "")
            if stage == "new":
                continue
            eligible.append(v)

        logger.info(
            "Maturity filter: %d eligible out of %d total (skipped 'new' < %d days)",
            len(eligible),
            len(videos),
            min_age,
        )
        return eligible

    def _crawl_video_comments(self, video: dict) -> list[CommentDTO]:
        video_id = video["video_id"]
        channel_id = video["channel_id"]
        max_comments = self._config.crawl.max_comments_per_video

        already_crawled = video.get("total_comments_crawled", 0)
        remaining = max(0, max_comments - already_crawled)
        if remaining <= 0:
            return []

        raw = self._downloader.download(video_id, max_comments=remaining)
        return self._downloader.to_comment_dtos(raw, video_id, channel_id)

    def _upload_to_gcs(self, comments: list[CommentDTO], video_id: str) -> None:
        now = datetime.now(timezone.utc)
        gcs_path = GCSClient.build_comments_path(video_id, now)
        payload = [c.to_dict() for c in comments]
        uri = self._gcs_client.upload_json(gcs_path, payload)
        logger.info("Uploaded %d comments for video %s to %s", len(comments), video_id, uri)

    def _update_crawl_state(self, video_id: str, comments_count: int) -> None:
        now = datetime.now(timezone.utc)
        self._crawl_state_repo.update_after_comment_crawl(
            video_id=video_id,
            comments_crawled_this_run=comments_count,
            crawled_at=now,
            max_comments_per_video=self._config.crawl.max_comments_per_video,
        )

    def get_channel_videos_historical(
        self,
        channel_id: str,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        raise NotImplementedError("CommentExtractor does not support video discovery")

    def get_channel_rss_videos(
        self,
        channel_id: str,
        published_after: datetime,
    ) -> list[dict]:
        raise NotImplementedError("CommentExtractor does not support video discovery")

    def search_videos_global(
        self,
        keyword: str,
        max_results: int,
    ) -> list[tuple[str, str]]:
        raise NotImplementedError("CommentExtractor does not support video discovery")

    def get_video_details(self, video_ids: list[str]) -> list[VideoDTO]:
        raise NotImplementedError("CommentExtractor does not support video discovery")

    def download_comments(
        self,
        video_id: str,
        channel_id: str,
        max_comments: int,
    ) -> list[CommentDTO]:
        raw = self._downloader.download(video_id, max_comments)
        return self._downloader.to_comment_dtos(raw, video_id, channel_id)