from __future__ import annotations

import logging
from datetime import datetime, timezone

from elt.datacontext.gcs_client import GCSClient
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.comment_downloader import CommentDownloader
from elt.repositories.crawl_state_repository import CrawlStateRepository

logger = logging.getLogger(__name__)


class CommentWorker:

    def __init__(
        self,
        downloader: CommentDownloader,
        crawl_state_repo: CrawlStateRepository,
        gcs_client: GCSClient,
        max_comments: int,
        new_video_min_age_days: int,
    ) -> None:
        self._downloader = downloader
        self._crawl_state_repo = crawl_state_repo
        self._gcs_client = gcs_client
        self._max_comments = max_comments
        self._min_age_days = new_video_min_age_days

    def process(self, video: VideoDTO) -> bool:
        if self._should_skip_by_maturity(video):
            logger.debug("Skipping video %s (too new)", video.video_id)
            return True

        raw = self._downloader.download(video.video_id, max_comments=self._max_comments)
        if not raw:
            self._crawl_state_repo.mark_video_skipped(video.video_id)
            logger.debug("No comments for video %s, marked skipped", video.video_id)
            return True

        comments = self._downloader.to_comment_dtos(raw, video.video_id, video.channel_id)
        if not comments:
            self._crawl_state_repo.mark_video_skipped(video.video_id)
            return True

        try:
            self._upload_to_gcs(comments, video.video_id)
            self._update_crawl_state(video.video_id, len(comments))
        except Exception:
            logger.exception("Failed to save comments for video %s", video.video_id)
            return False

        logger.info("Crawled %d comments for video %s", len(comments), video.video_id)
        return True

    def _should_skip_by_maturity(self, video: VideoDTO) -> bool:
        now = datetime.now(timezone.utc)
        age_days = (now - video.published_at).days
        return age_days < self._min_age_days

    def _upload_to_gcs(self, comments, video_id: str) -> None:
        now = datetime.now(timezone.utc)
        gcs_path = GCSClient.build_comments_path(video_id, now)
        payload = [c.to_dict() for c in comments]
        self._gcs_client.upload_json(gcs_path, payload)

    def _update_crawl_state(self, video_id: str, comments_count: int) -> None:
        now = datetime.now(timezone.utc)
        self._crawl_state_repo.update_after_comment_crawl(
            video_id=video_id,
            comments_crawled_this_run=comments_count,
            crawled_at=now,
            max_comments_per_video=self._max_comments,
        )
