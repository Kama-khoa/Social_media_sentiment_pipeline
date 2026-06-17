from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from googleapiclient.errors import HttpError

from elt.config import PipelineConfig
from elt.extract.helpers.youtube_api_comment_client import YouTubeApiCommentClient
from elt.quota_budget import QuotaBucket, QuotaBudget
from elt.repositories.api_comment_repository import ApiCommentRepository
from elt.repositories.quota_repository import QuotaRepository
from pipeline_progress import progress_bar

logger = logging.getLogger(__name__)

_COMMENT_THREADS_OPERATION = "comment_threads"
@dataclass
class ApiCommentBackfillResult:
    videos_seen: int
    videos_processed: int
    comments_merged: int
    quota_units_used: int
    dry_run: bool


class ApiCommentBackfill:
    def __init__(
        self,
        config: PipelineConfig,
        comment_client: YouTubeApiCommentClient,
        comment_repo: ApiCommentRepository,
        quota_repo: QuotaRepository | None = None,
    ) -> None:
        self._config = config
        self._comment_client = comment_client
        self._comment_repo = comment_repo
        self._quota_repo = quota_repo

    def run(
        self,
        dag_run_id: str,
        max_videos: int | None = None,
        max_comments_per_video: int | None = None,
        max_pages_per_video: int | None = None,
        quota_units: int | None = None,
        budget: QuotaBudget | None = None,
        dry_run: bool = False,
        product_id: str | None = None,
    ) -> ApiCommentBackfillResult:
        settings = self._config.api_comment_backfill
        max_videos = max_videos or settings.max_videos_per_run
        max_comments_per_video = max_comments_per_video or settings.max_comments_per_video
        max_pages_per_video = max_pages_per_video or settings.max_pages_per_video
        quota_units = quota_units or settings.daily_quota_units
        available_units = self._available_quota_units(quota_units, budget)

        if available_units <= 0:
            logger.warning("API comment backfill skipped: youtube_api_comments quota exhausted for today.")
            return ApiCommentBackfillResult(
                videos_seen=0,
                videos_processed=0,
                comments_merged=0,
                quota_units_used=0,
                dry_run=dry_run,
            )

        candidates = self._comment_repo.get_candidate_videos(max_videos, product_id=product_id)
        logger.info("API comment backfill candidates: %d", len(candidates))
        if dry_run:
            estimated_units = min(len(candidates) * max_pages_per_video, available_units)
            logger.info(
                "Dry run: max_videos=%d max_comments_per_video=%d max_pages_per_video=%d available_units=%d estimated_units<=%d",
                max_videos,
                max_comments_per_video,
                max_pages_per_video,
                available_units,
                estimated_units,
            )
            return ApiCommentBackfillResult(
                videos_seen=len(candidates),
                videos_processed=0,
                comments_merged=0,
                quota_units_used=0,
                dry_run=True,
            )

        comments_merged = 0
        quota_used = 0
        videos_processed = 0
        with progress_bar(candidates, desc="API comments", unit="video") as progress:
            for video in progress:
                if quota_used >= available_units:
                    logger.info("Stopping API backfill: quota cap reached (%d/%d)", quota_used, available_units)
                    break

                video_id = video["video_id"]
                channel_id = video.get("channel_id") or ""
                status = "done"
                error = None
                comments_collected = int(video.get("comments_collected") or 0)
                pages_crawled = int(video.get("pages_crawled") or 0)
                video_quota_used = int(video.get("quota_units_used") or 0)
                page_token = video.get("last_page_token")
                if page_token:
                    status = "in_progress"

                try:
                    while (
                        comments_collected < max_comments_per_video
                        and pages_crawled < max_pages_per_video
                        and quota_used < available_units
                    ):
                        if budget and not budget.can_consume(QuotaBucket.COMMENT_THREADS, 1):
                            logger.info(
                                "Stopping API backfill: QuotaBudget exhausted for %s",
                                QuotaBucket.COMMENT_THREADS.value,
                            )
                            break

                        page = self._comment_client.fetch_top_level_page(
                            video_id=video_id,
                            channel_id=channel_id,
                            page_token=page_token,
                            max_results=min(100, max_comments_per_video - comments_collected),
                        )
                        quota_used += page.quota_units_used
                        video_quota_used += page.quota_units_used
                        if budget:
                            budget.consume(QuotaBucket.COMMENT_THREADS, page.quota_units_used)
                        pages_crawled += 1
                        page_token = page.next_page_token

                        merged_this_page = self._comment_repo.merge_comments(page.comments)
                        comments_merged += merged_this_page
                        comments_collected += merged_this_page

                        if page_token and comments_collected < max_comments_per_video and pages_crawled < max_pages_per_video:
                            status = "in_progress"
                        elif comments_collected == 0:
                            status = "no_comments"
                        else:
                            status = "done"

                        self._comment_repo.update_backfill_state(
                            video_id=video_id,
                            channel_id=channel_id,
                            status=status,
                            comments_collected=comments_collected,
                            pages_crawled=pages_crawled,
                            quota_units_used=video_quota_used,
                            last_page_token=page_token,
                            last_error=None,
                        )

                        if not page.next_page_token:
                            break
                        if settings.request_delay_seconds > 0:
                            time.sleep(settings.request_delay_seconds)

                    if comments_collected == 0:
                        status = "no_comments"
                except HttpError as exc:
                    status = self._status_from_http_error(exc)
                    error = str(exc)[:1000]
                    logger.warning("API comment backfill failed for video_id=%s: %s", video_id, status)
                except Exception as exc:
                    status = "error"
                    error = str(exc)[:1000]
                    logger.exception("API comment backfill failed for video_id=%s", video_id)

                self._comment_repo.update_backfill_state(
                    video_id=video_id,
                    channel_id=channel_id,
                    status=status,
                    comments_collected=comments_collected,
                    pages_crawled=pages_crawled,
                    quota_units_used=video_quota_used,
                    last_page_token=page_token,
                    last_error=error,
                )
                videos_processed += 1
                progress.set_postfix(
                    comments=comments_merged,
                    quota=f"{quota_used}/{available_units}",
                    status=status,
                )

        if self._quota_repo:
            self._quota_repo.log_operation(
                operation_type=_COMMENT_THREADS_OPERATION,
                bucket=QuotaBucket.COMMENT_THREADS.value,
                units_used=quota_used,
                dag_run_id=dag_run_id,
                videos_processed=videos_processed,
                comments_collected=comments_merged,
            )

        return ApiCommentBackfillResult(
            videos_seen=len(candidates),
            videos_processed=videos_processed,
            comments_merged=comments_merged,
            quota_units_used=quota_used,
            dry_run=False,
        )

    @staticmethod
    def _status_from_http_error(exc: HttpError) -> str:
        try:
            reason = exc.error_details[0].get("reason")
        except (AttributeError, IndexError, TypeError):
            reason = None
        if reason == "commentsDisabled":
            return "comments_disabled"
        if reason in {"quotaExceeded", "dailyLimitExceeded"}:
            return "quota_exceeded"
        return "error"

    @staticmethod
    def _available_quota_units(requested_units: int, budget: QuotaBudget | None) -> int:
        if not budget:
            return requested_units

        remaining = budget.remaining(QuotaBucket.COMMENT_THREADS)
        available = min(requested_units, remaining)
        logger.info(
            "API comment quota: bucket=%s requested=%d budget_remaining=%d available=%d",
            QuotaBucket.COMMENT_THREADS.value,
            requested_units,
            remaining,
            available,
        )
        return available
