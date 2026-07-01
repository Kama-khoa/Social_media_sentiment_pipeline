from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from elt.datacontext.models.comment_dto import CommentDTO
from elt.extract.api_comment_backfill import ApiCommentBackfill
from elt.extract.helpers.youtube_api_comment_client import CommentPage
from elt.quota_budget import QuotaBucket, QuotaBudget


def _config():
    return SimpleNamespace(
        api_comment_backfill=SimpleNamespace(
            max_videos_per_run=10,
            max_comments_per_video=100,
            max_pages_per_video=1,
            daily_quota_units=100,
            request_delay_seconds=0,
        )
    )


def _budget(comment_threads_remaining: int = 100) -> QuotaBudget:
    budget = QuotaBudget(total=10000, safety_buffer=500)
    budget._remaining = {
        QuotaBucket.SEARCH: 9000,
        QuotaBucket.CHANNEL_SEED: 500,
        QuotaBucket.COMMENT_THREADS: comment_threads_remaining,
    }
    return budget


def _comment(comment_id: str) -> CommentDTO:
    return CommentDTO(
        comment_id=comment_id,
        video_id="v1",
        channel_id="c1",
        text_original="hello",
        is_reply=False,
        crawl_type="api_backfill",
        crawled_at=MagicMock(),
    )


def test_dry_run_does_not_fetch_or_merge_comments():
    comment_client = MagicMock()
    comment_repo = MagicMock()
    comment_repo.get_candidate_videos.return_value = [
        {"video_id": "v1", "channel_id": "c1"},
        {"video_id": "v2", "channel_id": "c2"},
    ]

    result = ApiCommentBackfill(_config(), comment_client, comment_repo).run(
        dag_run_id="run-1",
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.videos_seen == 2
    assert result.videos_processed == 0
    comment_client.fetch_top_level_page.assert_not_called()
    comment_repo.merge_comments.assert_not_called()


def test_run_limits_calls_to_remaining_logged_quota():
    comment_client = MagicMock()
    comment_client.fetch_top_level_page.return_value = CommentPage(
        comments=[],
        next_page_token=None,
        quota_units_used=1,
    )
    comment_repo = MagicMock()
    comment_repo.get_candidate_videos.return_value = [
        {"video_id": "v1", "channel_id": "c1"},
        {"video_id": "v2", "channel_id": "c2"},
    ]
    quota_repo = MagicMock()
    budget = _budget(comment_threads_remaining=1)

    result = ApiCommentBackfill(_config(), comment_client, comment_repo, quota_repo).run(
        dag_run_id="run-1",
        max_videos=2,
        quota_units=100,
        budget=budget,
    )

    assert result.quota_units_used == 1
    assert result.videos_processed == 1
    assert budget.remaining(QuotaBucket.COMMENT_THREADS) == 0
    comment_client.fetch_top_level_page.assert_called_once()
    quota_repo.log_operation.assert_called_once()


def test_run_merges_and_checkpoints_after_each_page():
    page1 = CommentPage(comments=[_comment("c1")], next_page_token="token-2", quota_units_used=1)
    page2 = CommentPage(comments=[_comment("c2")], next_page_token=None, quota_units_used=1)
    comment_client = MagicMock()
    comment_client.fetch_top_level_page.side_effect = [page1, page2]
    comment_repo = MagicMock()
    comment_repo.get_candidate_videos.return_value = [{"video_id": "v1", "channel_id": "c1"}]
    comment_repo.merge_comments.side_effect = lambda comments: len(comments)

    result = ApiCommentBackfill(_config(), comment_client, comment_repo, MagicMock()).run(
        dag_run_id="run-1",
        max_videos=1,
        max_pages_per_video=2,
        budget=_budget(),
    )

    assert result.comments_merged == 2
    assert result.quota_units_used == 2
    assert result.videos_processed == 1
    assert comment_repo.merge_comments.call_count == 2
    assert comment_repo.update_backfill_state.call_count == 3
    first_page_state = comment_repo.update_backfill_state.call_args_list[0].kwargs
    assert first_page_state["status"] == "in_progress"
    assert first_page_state["last_page_token"] == "token-2"
    final_state = comment_repo.update_backfill_state.call_args_list[-1].kwargs
    assert final_state["status"] == "done"


def test_resume_uses_last_page_token_from_candidate():
    comment_client = MagicMock()
    comment_client.fetch_top_level_page.return_value = CommentPage(
        comments=[_comment("c2")],
        next_page_token=None,
        quota_units_used=1,
    )
    comment_repo = MagicMock()
    comment_repo.get_candidate_videos.return_value = [{
        "video_id": "v1",
        "channel_id": "c1",
        "last_page_token": "resume-token",
        "comments_collected": 1,
        "pages_crawled": 1,
        "quota_units_used": 1,
    }]
    comment_repo.merge_comments.return_value = 1

    ApiCommentBackfill(_config(), comment_client, comment_repo, MagicMock()).run(
        dag_run_id="run-1",
        max_videos=1,
        max_pages_per_video=2,
        budget=_budget(),
    )

    assert comment_client.fetch_top_level_page.call_args.kwargs["page_token"] == "resume-token"


def test_crash_after_first_page_keeps_saved_page_checkpoint():
    page1 = CommentPage(comments=[_comment("c1")], next_page_token="token-2", quota_units_used=1)
    comment_client = MagicMock()
    comment_client.fetch_top_level_page.side_effect = [page1, RuntimeError("network")]
    comment_repo = MagicMock()
    comment_repo.get_candidate_videos.return_value = [{"video_id": "v1", "channel_id": "c1"}]
    comment_repo.merge_comments.return_value = 1

    result = ApiCommentBackfill(_config(), comment_client, comment_repo, MagicMock()).run(
        dag_run_id="run-1",
        max_videos=1,
        max_pages_per_video=2,
        budget=_budget(),
    )

    assert result.comments_merged == 1
    comment_repo.merge_comments.assert_called_once()
    first_page_state = comment_repo.update_backfill_state.call_args_list[0].kwargs
    assert first_page_state["status"] == "in_progress"
    assert first_page_state["last_page_token"] == "token-2"
    final_state = comment_repo.update_backfill_state.call_args_list[-1].kwargs
    assert final_state["status"] == "error"
    assert final_state["last_page_token"] == "token-2"
