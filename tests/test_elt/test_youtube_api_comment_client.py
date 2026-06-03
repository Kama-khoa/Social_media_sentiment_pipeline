from __future__ import annotations

from datetime import timezone
from unittest.mock import MagicMock, patch

from elt.extract.helpers.youtube_api_comment_client import YouTubeApiCommentClient


def test_fetch_top_level_page_parses_comment_threads():
    response = {
        "nextPageToken": "next-token",
        "items": [
            {
                "id": "thread-1",
                "snippet": {
                    "totalReplyCount": 2,
                    "topLevelComment": {
                        "id": "comment-1",
                        "snippet": {
                            "channelId": "UC_channel",
                            "textOriginal": "Pin tot",
                            "textDisplay": "Pin tot",
                            "authorDisplayName": "Tester",
                            "authorChannelId": {"value": "UC_author"},
                            "likeCount": 5,
                            "publishedAt": "2026-06-01T08:00:00Z",
                            "updatedAt": "2026-06-01T09:00:00Z",
                        },
                    },
                },
            }
        ],
    }
    execute = MagicMock(return_value=response)
    list_call = MagicMock(return_value=MagicMock(execute=execute))
    service = MagicMock()
    service.commentThreads.return_value.list = list_call

    with patch("elt.extract.helpers.youtube_api_comment_client.build", return_value=service):
        client = YouTubeApiCommentClient("api-key")
        page = client.fetch_top_level_page("video-1", "UC_channel")

    assert page.next_page_token == "next-token"
    assert page.quota_units_used == 1
    assert len(page.comments) == 1
    comment = page.comments[0]
    assert comment.comment_id == "comment-1"
    assert comment.video_id == "video-1"
    assert comment.channel_id == "UC_channel"
    assert comment.text_original == "Pin tot"
    assert comment.like_count == 5
    assert comment.reply_count == 2
    assert comment.crawl_type == "api_backfill"
    assert comment.published_at is not None
    assert comment.published_at.tzinfo == timezone.utc


def test_fetch_top_level_page_skips_empty_text():
    response = {
        "items": [
            {
                "id": "thread-1",
                "snippet": {
                    "topLevelComment": {
                        "id": "comment-1",
                        "snippet": {"textOriginal": ""},
                    },
                },
            }
        ],
    }
    execute = MagicMock(return_value=response)
    service = MagicMock()
    service.commentThreads.return_value.list.return_value.execute = execute

    with patch("elt.extract.helpers.youtube_api_comment_client.build", return_value=service):
        client = YouTubeApiCommentClient("api-key")
        page = client.fetch_top_level_page("video-1", "UC_channel")

    assert page.comments == []
