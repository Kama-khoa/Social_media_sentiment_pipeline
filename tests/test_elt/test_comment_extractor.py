from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.comment_dto import CommentDTO
from elt.extract.comment_extractor import CommentExtractor


def _make_config() -> MagicMock:
    cfg = MagicMock()
    cfg.crawl.max_comments_per_video = 500
    cfg.crawl.new_video_min_age_days = 3
    cfg.comment_downloader.request_delay_seconds = 0
    cfg.comment_downloader.max_retries = 3
    return cfg


def _sample_comment(cid: str = "c1", video_id: str = "vid_1") -> CommentDTO:
    return CommentDTO(
        comment_id=cid,
        video_id=video_id,
        channel_id="UC_ch",
        text_original="Pin trâu lắm",
        is_reply=False,
        crawl_type="full",
        crawled_at=datetime.now(timezone.utc),
    )


CRAWL_STATE_VIDEOS = [
    {
        "video_id": "vid_new",
        "channel_id": "UC_ch",
        "comment_count": 100,
        "total_comments_crawled": 0,
        "maturity_stage": "new",
    },
    {
        "video_id": "vid_growing",
        "channel_id": "UC_ch",
        "comment_count": 500,
        "total_comments_crawled": 100,
        "maturity_stage": "growing",
    },
    {
        "video_id": "vid_mature",
        "channel_id": "UC_ch",
        "comment_count": 800,
        "total_comments_crawled": 200,
        "maturity_stage": "mature",
    },
    {
        "video_id": "vid_archived",
        "channel_id": "UC_ch",
        "comment_count": 300,
        "total_comments_crawled": 300,
        "maturity_stage": "archived",
    },
]


@pytest.fixture
def deps() -> dict:
    return {
        "crawl_state_repo": MagicMock(),
        "quota_repo": MagicMock(),
        "gcs_client": MagicMock(),
    }


@pytest.fixture
def extractor(deps: dict) -> CommentExtractor:
    ext = CommentExtractor(
        config=_make_config(),
        crawl_state_repo=deps["crawl_state_repo"],
        quota_repo=deps["quota_repo"],
        gcs_client=deps["gcs_client"],
        proxy_config=None,
    )
    return ext


class TestApplyMaturityFilter:
    def test_skips_new_videos(self, extractor: CommentExtractor):
        result = extractor._apply_maturity_filter(CRAWL_STATE_VIDEOS)

        stages = [v["maturity_stage"] for v in result]
        assert "new" not in stages
        assert "growing" in stages
        assert "mature" in stages
        assert "archived" in stages

    def test_empty_input(self, extractor: CommentExtractor):
        assert extractor._apply_maturity_filter([]) == []


class TestCrawlVideoComments:
    def test_respects_remaining_quota(self, extractor: CommentExtractor):
        video = {
            "video_id": "vid_1",
            "channel_id": "UC_ch",
            "total_comments_crawled": 450,
        }

        with patch.object(extractor._downloader, "download", return_value=[]) as mock_dl:
            with patch.object(extractor._downloader, "to_comment_dtos", return_value=[]):
                extractor._crawl_video_comments(video)

                mock_dl.assert_called_once_with("vid_1", max_comments=50)

    def test_returns_empty_when_already_complete(self, extractor: CommentExtractor):
        video = {
            "video_id": "vid_1",
            "channel_id": "UC_ch",
            "total_comments_crawled": 500,
        }

        result = extractor._crawl_video_comments(video)

        assert result == []


class TestUploadToGcs:
    def test_uploads_comments(self, extractor: CommentExtractor, deps: dict):
        comments = [_sample_comment("c1"), _sample_comment("c2")]
        deps["gcs_client"].upload_json.return_value = "gs://bucket/path.json"

        extractor._upload_to_gcs(comments, "vid_1")

        deps["gcs_client"].upload_json.assert_called_once()
        args = deps["gcs_client"].upload_json.call_args
        assert len(args[0][1]) == 2
        assert "comments" in args[0][0]


class TestUpdateCrawlState:
    def test_calls_repository(self, extractor: CommentExtractor, deps: dict):
        extractor._update_crawl_state("vid_1", 50)

        deps["crawl_state_repo"].update_after_comment_crawl.assert_called_once()
        call_kwargs = deps["crawl_state_repo"].update_after_comment_crawl.call_args[1]
        assert call_kwargs["video_id"] == "vid_1"
        assert call_kwargs["comments_crawled_this_run"] == 50
        assert call_kwargs["max_comments_per_video"] == 500


class TestRun:
    def test_full_run_flow(self, extractor: CommentExtractor, deps: dict):
        deps["crawl_state_repo"].get_videos_to_crawl.return_value = CRAWL_STATE_VIDEOS
        deps["gcs_client"].upload_json.return_value = "gs://bucket/path.json"

        comments = [_sample_comment("c1", "vid_growing"), _sample_comment("c2", "vid_growing")]
        with patch.object(extractor._downloader, "download", return_value=[{"cid": "c1", "text": "ok"}]):
            with patch.object(extractor._downloader, "to_comment_dtos", return_value=comments):
                result = extractor.run("dag_run_test")

        assert result["videos_crawled"] >= 0
        assert result["total_comments"] >= 0
        deps["quota_repo"].log_operation.assert_called_once()

    def test_skips_video_with_no_comments(self, extractor: CommentExtractor, deps: dict):
        deps["crawl_state_repo"].get_videos_to_crawl.return_value = [
            {
                "video_id": "vid_empty",
                "channel_id": "UC_ch",
                "comment_count": 0,
                "total_comments_crawled": 0,
                "maturity_stage": "growing",
            },
        ]

        with patch.object(extractor._downloader, "download", return_value=[]):
            with patch.object(extractor._downloader, "to_comment_dtos", return_value=[]):
                result = extractor.run("dag_run_test")

        assert result["videos_skipped"] == 1
        deps["crawl_state_repo"].mark_video_skipped.assert_called_once_with("vid_empty")
