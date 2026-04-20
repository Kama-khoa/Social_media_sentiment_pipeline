from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from itertools import groupby
from operator import attrgetter
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
from elt.quota_budget import QuotaBucket, QuotaBudget
from elt.repositories.channel_repository import ChannelRepository
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.keyword_repository import KeywordRepository
from elt.repositories.quota_repository import QuotaRepository

logger = logging.getLogger(__name__)

_SEARCH_UNITS_PER_CALL = 100
_VIDEOS_LIST_UNITS_PER_CALL = 1
_SKIP_CLUSTERS = {"_uncategorized"}


class VideoExtractor(BaseExtractor):

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
        self._rss_reader = RssFeedReader()

    def run(
        self,
        execution_date: str,
        dag_run_id: str,
        budget: QuotaBudget,
    ) -> dict:
        t0 = time.monotonic()
        keywords = self._keyword_repo.get_active_keywords()

        # mode0_videos = self._run_mode_0_historical(budget, keywords)
        mode1_videos = self._run_mode_1_rss(execution_date, keywords)
        # mode2_videos = self._run_mode_2_keyword_sweep(budget, keywords)

        # all_candidates = mode0_videos + mode1_videos + mode2_videos
        all_candidates =  mode1_videos

        enriched = self._deduplicate_and_enrich(all_candidates, budget)

        if enriched:
            try:
                self._upload_to_gcs(enriched, execution_date)
                self._save_to_crawl_state(enriched)
            except Exception as e:
                logger.error("Lỗi khi lưu trữ dữ liệu. Hủy bỏ cập nhật trạng thái: %s", e)
                raise e

        elapsed = time.monotonic() - t0
        self._quota_repo.log_operation(
            operation_type="video_extraction",
            bucket=QuotaBucket.SEARCH.value,
            units_used=0,
            dag_run_id=dag_run_id,
            videos_processed=len(enriched),
            execution_time_seconds=elapsed,
        )

        return {
            # "mode0": len(mode0_videos),
            "mode1": len(mode1_videos),
            # "mode2": len(mode2_videos),
            "total_enriched": len(enriched),
            "elapsed_seconds": round(elapsed, 2),
        }

    def _run_mode_0_historical(
        self,
        budget: QuotaBudget,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        limit = self._config.crawl.historical_scan_channels_per_day
        channels = self._channel_repo.get_unscanned_channels(limit=limit)
        if not channels:
            return []

        fetcher = YtdlpVideoFetcher(keywords)
        all_videos: list[VideoDTO] = []

        for ch in channels:
            url = ch.channel_url or f"https://www.youtube.com/{ch.channel_handle}"
            logger.info("Mode 0: scanning channel %s (%s)", ch.channel_name, url)

            raw = fetcher.fetch_channel_videos(url)
            matched = fetcher.filter_by_keywords(raw)
            dtos = fetcher.to_video_dtos(matched, ch.channel_id)
            all_videos.extend(dtos)

            self._channel_repo.mark_historically_scanned(ch.channel_id)
            logger.info("Mode 0: channel %s done, %d videos matched", ch.channel_name, len(dtos))

        return all_videos

    def _run_mode_1_rss(
        self,
        execution_date: str,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        channels = self._channel_repo.get_active_channels()
        published_after = datetime.fromisoformat(execution_date).replace(
            tzinfo=timezone.utc
        ) - timedelta(days=1)

        keyword_texts_lower = {kw.keyword_text.lower(): kw.keyword_text for kw in keywords}
        now = datetime.now(timezone.utc)
        all_videos: list[VideoDTO] = []

        for ch in channels:
            entries = self._rss_reader.fetch_feed(ch.channel_id)
            recent = self._rss_reader.filter_by_date(entries, published_after)

            for entry in recent:
                title_lower = entry.get("title", "").lower()
                matched_kw: Optional[str] = None
                for kw_lower, kw_original in keyword_texts_lower.items():
                    if kw_lower in title_lower:
                        matched_kw = kw_original
                        break

                all_videos.append(VideoDTO(
                    video_id=entry["video_id"],
                    channel_id=ch.channel_id,
                    title=entry.get("title", ""),
                    published_at=entry.get("published_at") or now,
                    search_mode="MODE1",
                    crawled_at=now,
                    keyword_matched=matched_kw,
                ))

        logger.info("Mode 1: %d videos from RSS across %d channels", len(all_videos), len(channels))
        return all_videos

    def _run_mode_2_keyword_sweep(
        self,
        budget: QuotaBudget,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        queries = self._build_mode2_search_queries(keywords)
        max_results = self._config.crawl.keyword_search_max_results
        now = datetime.now(timezone.utc)
        all_videos: list[VideoDTO] = []

        for query_text, cluster_name in queries:
            if not budget.can_consume(QuotaBucket.SEARCH, _SEARCH_UNITS_PER_CALL):
                logger.warning("Mode 2: quota exhausted, stopping keyword sweep")
                break

            pairs = self._api_client.search_videos(
                keyword=query_text,
                max_results=max_results,
                search_cluster=cluster_name,
            )
            budget.consume(QuotaBucket.SEARCH, _SEARCH_UNITS_PER_CALL)

            for video_id, channel_id in pairs:
                all_videos.append(VideoDTO(
                    video_id=video_id,
                    channel_id=channel_id,
                    title="",
                    published_at=now,
                    search_mode="MODE2",
                    crawled_at=now,
                    keyword_matched=query_text,
                ))

        logger.info("Mode 2: %d videos from %d search queries", len(all_videos), len(queries))
        return all_videos

    def _build_mode2_search_queries(
        self,
        keywords: list[KeywordDTO],
    ) -> list[tuple[str, str]]:
        keyword_text_set = {kw.keyword_text for kw in keywords}
        sorted_kws = sorted(keywords, key=attrgetter("search_cluster"))
        queries: list[tuple[str, str]] = []

        for cluster, group in groupby(sorted_kws, key=attrgetter("search_cluster")):
            if not cluster or cluster in _SKIP_CLUSTERS:
                continue

            kw_list = list(group)
            is_specific = cluster in keyword_text_set

            if is_specific:
                queries.append((cluster, cluster))
            else:
                for kw in kw_list:
                    queries.append((kw.keyword_text, cluster))

        return queries

    def _deduplicate_and_enrich(
        self,
        candidates: list[VideoDTO],
        budget: QuotaBudget,
    ) -> list[VideoDTO]:
        seen: dict[str, VideoDTO] = {}
        for v in candidates:
            if v.video_id not in seen:
                seen[v.video_id] = v

        unique_ids = list(seen.keys())
        if not unique_ids:
            return []

        needs_enrich = [
            vid for vid, dto in seen.items()
            if dto.view_count is None
        ]

        if needs_enrich:
            batch_count = (len(needs_enrich) + 49) // 50
            units_needed = batch_count * _VIDEOS_LIST_UNITS_PER_CALL

            if budget.can_consume(QuotaBucket.SEARCH, units_needed):
                budget.consume(QuotaBucket.SEARCH, units_needed)
                enriched_dtos = self._api_client.get_video_details(needs_enrich)
                for dto in enriched_dtos:
                    original = seen.get(dto.video_id)
                    if original:
                        dto.search_mode = original.search_mode
                        dto.keyword_matched = original.keyword_matched
                        seen[dto.video_id] = dto
            else:
                logger.warning("Not enough quota to enrich %d videos", len(needs_enrich))

        return list(seen.values())

    def _save_to_crawl_state(self, videos: list[VideoDTO]) -> None:
        self._crawl_state_repo.bulk_upsert_from_video_dtos(videos)
        logger.info("Saved %d videos to crawl_state", len(videos))

    def _upload_to_gcs(self, videos: list[VideoDTO], execution_date: str) -> None:
        now = datetime.now(timezone.utc)
        gcs_path = GCSClient.build_videos_path(now)
        payload = [v.to_dict() for v in videos]
        uri = self._gcs_client.upload_json(gcs_path, payload)
        logger.info("Uploaded %d videos to %s", len(videos), uri)

    def get_channel_videos_historical(
        self,
        channel_id: str,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        fetcher = YtdlpVideoFetcher(keywords)
        channels = self._channel_repo.get_active_channels()
        ch = next((c for c in channels if c.channel_id == channel_id), None)
        if ch is None:
            return []
        url = ch.channel_url or f"https://www.youtube.com/{ch.channel_handle}"
        raw = fetcher.fetch_channel_videos(url)
        matched = fetcher.filter_by_keywords(raw)
        return fetcher.to_video_dtos(matched, channel_id)

    def get_channel_rss_videos(
        self,
        channel_id: str,
        published_after: datetime,
    ) -> list[dict]:
        return self._rss_reader.filter_by_date(
            self._rss_reader.fetch_feed(channel_id),
            published_after,
        )

    def search_videos_global(
        self,
        keyword: str,
        max_results: int,
    ) -> list[tuple[str, str]]:
        return self._api_client.search_videos(keyword, max_results)

    def get_video_details(self, video_ids: list[str]) -> list[VideoDTO]:
        return self._api_client.get_video_details(video_ids)

    def download_comments(
        self,
        video_id: str,
        channel_id: str,
        max_comments: int,
    ) -> list[CommentDTO]:
        proxy_cfg = ProxyConfig(
            host=self._config.brightdata_proxy_host,
            port=int(self._config.brightdata_proxy_port),
            username=self._config.brightdata_username,
            password=self._config.brightdata_password,
        )
        downloader = CommentDownloader(proxy_cfg)
        raw = downloader.download(video_id, max_comments)
        return downloader.to_comment_dtos(raw, video_id, channel_id)