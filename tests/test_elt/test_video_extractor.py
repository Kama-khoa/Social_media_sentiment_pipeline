from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.channel_dto import ChannelDTO
from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpFetchError
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
    cfg.crawl.historical_scan_lookback_days = 730
    cfg.crawl.video_batch_size = 50
    cfg.crawl.historical_scan_max_results = 10000
    return cfg


def _make_budget(search_remaining: int = 9000) -> QuotaBudget:
    budget = QuotaBudget(total=10000, safety_buffer=500)
    budget._remaining = {
        QuotaBucket.SEARCH: search_remaining,
        QuotaBucket.CHANNEL_SEED: 500,
        QuotaBucket.COMMENT_THREADS: 5000,
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


class TestRunHistorical:
    def test_does_not_mark_channel_scanned_when_ytdlp_fetch_fails(
        self,
        extractor: VideoExtractor,
        deps: dict,
    ):
        extractor._config.crawl.historical_scan_channels_per_day = 1
        extractor._config.crawl.historical_scan_lookback_days = 180
        extractor._config.crawl.video_batch_size = 5
        deps["channel_repo"].get_unscanned_channels.return_value = [_sample_channel()]

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_channel_videos.side_effect = YtdlpFetchError("network")
        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        result = extractor.run_historical("2026-05-20", "dag_run_test", _make_budget())

        assert result["channels_scanned"] == 0
        deps["channel_repo"].mark_historically_scanned.assert_not_called()

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

    def test_does_not_mark_channel_scanned_when_raw_videos_is_empty(
        self,
        extractor: VideoExtractor,
        deps: dict,
    ):
        extractor._config.crawl.historical_scan_channels_per_day = 1
        deps["channel_repo"].get_unscanned_channels.return_value = [_sample_channel()]

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_channel_videos.return_value = []
        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        result = extractor.run_historical("2026-05-20", "dag_run_test", _make_budget())

        assert result["channels_scanned"] == 0
        deps["channel_repo"].mark_historically_scanned.assert_not_called()

    def test_unexpected_exception_in_processing_loop_leaves_channel_pending(
        self,
        extractor: VideoExtractor,
        deps: dict,
    ):
        extractor._config.crawl.historical_scan_channels_per_day = 2
        extractor._config.crawl.video_batch_size = 5
        ch1 = _sample_channel(channel_id="UC_1")
        ch2 = _sample_channel(channel_id="UC_2")
        deps["channel_repo"].get_unscanned_channels.return_value = [ch1, ch2]

        raw_videos = [{"id": "vid_1", "upload_date": "20260515", "title": "Video 1"}]

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_channel_videos.return_value = raw_videos
        mock_fetcher.filter_by_keywords.side_effect = lambda videos: videos
        # Throw an unexpected exception during batch enrich for the first channel, and succeed (return empty list) for the second
        mock_fetcher.enrich_batch.side_effect = [Exception("unexpected database failure"), []]
        mock_fetcher.build_video_dtos.return_value = []

        def mock_parse(entry):
            return datetime(2026, 5, 15, tzinfo=timezone.utc)
        mock_fetcher._parse_published_at.side_effect = mock_parse

        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        # Run historical scan
        result = extractor.run_historical("2026-05-20", "dag_run_test", _make_budget())

        # The first channel UC_1 should have failed, but UC_2 should be scanned successfully (even if it has no new videos)
        assert result["channels_scanned"] == 1
        # mark_historically_scanned should be called exactly once (for ch2, UC_2)
        deps["channel_repo"].mark_historically_scanned.assert_called_once_with("UC_2")


class TestRunManualChannel:
    @patch("elt.extract.video_extractor.datetime")
    def test_manual_channel_falls_back_to_ytdlp_when_search_quota_is_empty(
        self,
        mock_datetime: MagicMock,
        extractor: VideoExtractor,
        deps: dict,
    ):
        now = datetime(2026, 5, 20, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now
        deps["channel_repo"].get_active_channel.return_value = _sample_channel()
        deps["crawl_state_repo"].get_existing_video_ids.return_value = set()

        raw_videos = [{"id": "vid_1", "upload_date": "20260518", "title": "Samsung Galaxy S25 review"}]
        dto = VideoDTO(
            video_id="vid_1",
            channel_id="UC_test",
            title="Samsung Galaxy S25 review",
            published_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
            search_mode="MANUAL",
            crawled_at=now,
        )

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_channel_videos.return_value = raw_videos
        mock_fetcher._parse_published_at.return_value = datetime(2026, 5, 18, tzinfo=timezone.utc)
        mock_fetcher.filter_by_keywords.side_effect = lambda videos: videos
        mock_fetcher.enrich_batch.side_effect = lambda videos: videos
        mock_fetcher.build_video_dtos.return_value = [dto]
        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        result = extractor.run_manual_channel(
            channel_id="UC_test",
            lookback_days=7,
            crawl_mode="api_or_ytdlp",
            execution_date="2026-05-20",
            dag_run_id="manual_test",
            budget=_make_budget(search_remaining=0),
        )

        assert result["crawl_mode"] == "ytdlp"
        assert result["total_saved"] == 1
        mock_fetcher.fetch_channel_videos.assert_called_once()
        extractor._api_client.search_channel_recent.assert_not_called()
        deps["channel_repo"].mark_historically_scanned.assert_not_called()

    @patch("elt.extract.video_extractor.datetime")
    def test_manual_channel_uses_api_when_quota_is_available(
        self,
        mock_datetime: MagicMock,
        extractor: VideoExtractor,
        deps: dict,
    ):
        now = datetime(2026, 5, 20, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now
        deps["channel_repo"].get_active_channel.return_value = _sample_channel()
        deps["crawl_state_repo"].get_existing_video_ids.return_value = set()
        extractor._api_client.search_channel_recent.return_value = [
            {"id": "vid_1", "published_at": datetime(2026, 5, 19, tzinfo=timezone.utc)}
        ]

        dto = VideoDTO(
            video_id="vid_1",
            channel_id="UC_test",
            title="Samsung Galaxy S25 review",
            published_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
            search_mode="MANUAL",
            crawled_at=now,
        )

        mock_fetcher = MagicMock()
        mock_fetcher.filter_by_keywords.side_effect = lambda videos: videos
        mock_fetcher.enrich_batch.side_effect = lambda videos: videos
        mock_fetcher.build_video_dtos.return_value = [dto]
        extractor._build_fetcher = MagicMock(return_value=mock_fetcher)

        budget = _make_budget(search_remaining=100)
        result = extractor.run_manual_channel(
            channel_id="UC_test",
            lookback_days=3,
            crawl_mode="api_or_ytdlp",
            execution_date="2026-05-20",
            dag_run_id="manual_test",
            budget=budget,
        )

        assert result["crawl_mode"] == "api_or_ytdlp"
        assert result["total_saved"] == 1
        assert budget.remaining(QuotaBucket.SEARCH) == 0
        extractor._api_client.search_channel_recent.assert_called_once()
        mock_fetcher.fetch_channel_videos.assert_not_called()
        deps["channel_repo"].mark_historically_scanned.assert_not_called()
