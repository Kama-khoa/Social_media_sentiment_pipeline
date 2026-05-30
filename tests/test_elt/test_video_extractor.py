from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.channel_dto import ChannelDTO
from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.video_extractor import VideoExtractor
from elt.quota_budget import QuotaBucket, QuotaBudget


def _make_config() -> MagicMock:
    cfg = MagicMock()
    cfg.youtube_api_key = "fake-key"
    cfg.brightdata_proxy_host = "proxy.test"
    cfg.brightdata_proxy_port = "22225"
    cfg.brightdata_username = "user"
    cfg.brightdata_password = "pass"
    cfg.crawl.historical_scan_channels_per_day = 2
    cfg.crawl.keyword_search_max_results = 5
    cfg.crawl.max_comments_per_video = 500
    return cfg


def _make_budget(search_remaining: int = 9000) -> QuotaBudget:
    budget = QuotaBudget(total=10000, safety_buffer=500)
    budget._remaining = {
        QuotaBucket.SEARCH: search_remaining,
        QuotaBucket.CHANNEL_SEED: 500,
    }
    return budget


def _sample_channel(channel_id: str = "UC_test", scanned: bool = False) -> ChannelDTO:
    return ChannelDTO(
        channel_id=channel_id,
        channel_name="Test Channel",
        channel_url="https://www.youtube.com/@testchannel",
        channel_handle="@testchannel",
        subscriber_count=100000,
        is_active=True,
        is_historically_scanned=scanned,
    )


KEYWORDS = [
    KeywordDTO(keyword_id="kw_001", keyword_text="Samsung Galaxy S25", search_cluster="Samsung Galaxy S25"),
    KeywordDTO(keyword_id="kw_002", keyword_text="Samsung Galaxy S25 review", search_cluster="Samsung Galaxy S25"),
    KeywordDTO(keyword_id="kw_003", keyword_text="điện thoại tầm 5 triệu", search_cluster="Điện thoại tầm 5 triệu"),
    KeywordDTO(keyword_id="kw_004", keyword_text="review", search_cluster="_uncategorized"),
]


@pytest.fixture
def deps() -> dict:
    return {
        "channel_repo": MagicMock(),
        "keyword_repo": MagicMock(),
        "crawl_state_repo": MagicMock(),
        "quota_repo": MagicMock(),
        "gcs_client": MagicMock(),
    }


@pytest.fixture
def extractor(deps: dict) -> VideoExtractor:
    with patch("elt.extract.video_extractor.YouTubeApiClient"):
        return VideoExtractor(
            config=_make_config(),
            channel_repo=deps["channel_repo"],
            keyword_repo=deps["keyword_repo"],
            crawl_state_repo=deps["crawl_state_repo"],
            quota_repo=deps["quota_repo"],
            gcs_client=deps["gcs_client"],
        )


class TestBuildMode2SearchQueries:
    def test_specific_cluster_one_call(self, extractor: VideoExtractor):
        queries = extractor._build_mode2_search_queries(KEYWORDS)

        specific = [q for q in queries if q[1] == "Samsung Galaxy S25"]
        assert len(specific) == 1
        assert specific[0][0] == "Samsung Galaxy S25"

    def test_comparison_cluster_per_keyword(self, extractor: VideoExtractor):
        queries = extractor._build_mode2_search_queries(KEYWORDS)

        comparison = [q for q in queries if q[1] == "Điện thoại tầm 5 triệu"]
        assert len(comparison) == 1
        assert comparison[0][0] == "điện thoại tầm 5 triệu"

    def test_skips_uncategorized(self, extractor: VideoExtractor):
        queries = extractor._build_mode2_search_queries(KEYWORDS)

        uncategorized = [q for q in queries if q[1] == "_uncategorized"]
        assert len(uncategorized) == 0

    def test_skips_none_cluster(self, extractor: VideoExtractor):
        kws = [KeywordDTO(keyword_id="kw_x", keyword_text="test", search_cluster=None)]
        queries = extractor._build_mode2_search_queries(kws)
        assert queries == []


class TestDeduplicateAndEnrich:
    def test_deduplicates_by_video_id(self, extractor: VideoExtractor):
        now = datetime.now(timezone.utc)
        v1 = VideoDTO(video_id="vid_1", channel_id="ch", title="A", published_at=now, search_mode="MODE0", crawled_at=now, view_count=100)
        v2 = VideoDTO(video_id="vid_1", channel_id="ch", title="B", published_at=now, search_mode="MODE1", crawled_at=now, view_count=200)
        v3 = VideoDTO(video_id="vid_2", channel_id="ch", title="C", published_at=now, search_mode="MODE2", crawled_at=now, view_count=300)

        budget = _make_budget()
        result = extractor._deduplicate_and_enrich([v1, v2, v3], budget)

        ids = [v.video_id for v in result]
        assert len(ids) == 2
        assert ids.count("vid_1") == 1
        assert "vid_2" in ids

    def test_enriches_videos_without_view_count(self, extractor: VideoExtractor):
        now = datetime.now(timezone.utc)
        v1 = VideoDTO(video_id="vid_1", channel_id="ch", title="A", published_at=now, search_mode="MODE2", crawled_at=now, view_count=None)

        enriched_dto = VideoDTO(
            video_id="vid_1", channel_id="ch", title="A enriched",
            published_at=now, search_mode="MODE2", crawled_at=now,
            view_count=50000, like_count=1000,
        )
        extractor._api_client.get_video_details.return_value = [enriched_dto]

        budget = _make_budget()
        result = extractor._deduplicate_and_enrich([v1], budget)

        assert result[0].view_count == 50000
        assert result[0].search_mode == "MODE2"

    def test_returns_empty_for_no_candidates(self, extractor: VideoExtractor):
        budget = _make_budget()
        result = extractor._deduplicate_and_enrich([], budget)
        assert result == []


class TestRun:
    def test_full_run_orchestrates_all_modes(self, extractor: VideoExtractor, deps: dict):
        now = datetime.now(timezone.utc)
        deps["keyword_repo"].get_active_keywords.return_value = KEYWORDS[:2]
        deps["channel_repo"].get_unscanned_channels.return_value = []
        deps["channel_repo"].get_active_channels.return_value = []
        extractor._api_client.search_videos.return_value = [("vid_m2", "ch_m2")]
        extractor._api_client.get_video_details.return_value = [
            VideoDTO(video_id="vid_m2", channel_id="ch_m2", title="Enriched",
                     published_at=now, search_mode="MODE2", crawled_at=now, view_count=1000),
        ]
        deps["gcs_client"].upload_json.return_value = "gs://bucket/path.json"

        budget = _make_budget()
        result = extractor.run("2026-03-15", "dag_run_test", budget)

        assert result["mode0"] == 0
        assert result["mode1"] == 0
        assert result["total_enriched"] >= 0
        deps["quota_repo"].log_operation.assert_called_once()


class TestRunHistorical:
    @patch("elt.extract.video_extractor.datetime")
    def test_run_historical_filters_by_lookback_days(self, mock_datetime: MagicMock, extractor: VideoExtractor, deps: dict):
        mock_now = datetime(2026, 5, 20, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        extractor._config.crawl.historical_scan_lookback_days = 10
        extractor._config.crawl.historical_scan_channels_per_day = 1
        extractor._config.crawl.video_batch_size = 5

        raw_videos = [
            {"id": "vid_new", "upload_date": "20260515", "title": "New Video"},
            {"id": "vid_old", "upload_date": "20260505", "title": "Old Video"},
        ]

        ch = ChannelDTO(
            channel_id="UC_test",
            channel_name="Test",
            channel_url="https://www.youtube.com/@test",
            channel_handle="@test",
            subscriber_count=100,
            is_active=True,
            is_historically_scanned=False
        )
        deps["channel_repo"].get_unscanned_channels.return_value = [ch]
        deps["crawl_state_repo"].get_existing_video_ids.return_value = []

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_channel_videos.return_value = raw_videos

        def mock_parse(entry):
            up_date = entry.get("upload_date")
            if up_date:
                return datetime.strptime(up_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            return None
        mock_fetcher._parse_published_at.side_effect = mock_parse
        mock_fetcher.filter_by_keywords.side_effect = lambda videos: videos
        mock_fetcher.enrich_batch.side_effect = lambda videos: videos
        mock_fetcher.build_video_dtos.return_value = []

        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        budget = _make_budget()
        extractor.run_historical("2026-05-20", "dag_run_test", budget)

        mock_fetcher.filter_by_keywords.assert_called_once()
        filtered_arg = mock_fetcher.filter_by_keywords.call_args[0][0]
        assert len(filtered_arg) == 1
        assert filtered_arg[0]["id"] == "vid_new"

