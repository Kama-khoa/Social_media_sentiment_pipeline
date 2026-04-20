from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.youtube_api_client import YouTubeApiClient


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_service: MagicMock) -> YouTubeApiClient:
    with patch("elt.extract.helpers.youtube_api_client.build", return_value=mock_service):
        return YouTubeApiClient(api_key="fake-key")


SEARCH_RESPONSE = {
    "items": [
        {
            "id": {"videoId": "vid_001"},
            "snippet": {"channelId": "UC_ch1"},
        },
        {
            "id": {"videoId": "vid_002"},
            "snippet": {"channelId": "UC_ch2"},
        },
    ]
}

VIDEOS_LIST_RESPONSE = {
    "items": [
        {
            "id": "vid_001",
            "snippet": {
                "channelId": "UC_ch1",
                "title": "Test Video",
                "description": "A test",
                "publishedAt": "2026-03-15T08:00:00Z",
                "tags": ["test", "review"],
                "thumbnails": {
                    "high": {"url": "https://img.youtube.com/vi/vid_001/hqdefault.jpg"},
                },
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "5000",
                "commentCount": "1200",
            },
            "contentDetails": {
                "duration": "PT10M30S",
            },
        }
    ]
}


class TestSearchVideos:
    def test_returns_video_channel_pairs(self, client: YouTubeApiClient, mock_service: MagicMock):
        mock_service.search().list().execute.return_value = SEARCH_RESPONSE

        result = client.search_videos("Samsung Galaxy S25", max_results=10)

        assert len(result) == 2
        assert result[0] == ("vid_001", "UC_ch1")
        assert result[1] == ("vid_002", "UC_ch2")

    def test_skips_uncategorized_cluster(self, client: YouTubeApiClient, mock_service: MagicMock):
        result = client.search_videos(
            "review",
            max_results=10,
            search_cluster="_uncategorized",
        )

        assert result == []
        mock_service.search().list().execute.assert_not_called()

    def test_returns_empty_on_exception(self, client: YouTubeApiClient, mock_service: MagicMock):
        mock_service.search().list().execute.side_effect = Exception("API error")

        result = client.search_videos("test keyword")

        assert result == []


class TestGetVideoDetails:
    def test_returns_dtos(self, client: YouTubeApiClient, mock_service: MagicMock):
        mock_service.videos().list().execute.return_value = VIDEOS_LIST_RESPONSE

        result = client.get_video_details(["vid_001"])

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, VideoDTO)
        assert dto.video_id == "vid_001"
        assert dto.channel_id == "UC_ch1"
        assert dto.title == "Test Video"
        assert dto.view_count == 150000
        assert dto.like_count == 5000
        assert dto.comment_count == 1200
        assert dto.duration_seconds == 630
        assert dto.search_mode == "MODE2"
        assert dto.tags == ["test", "review"]

    def test_empty_ids(self, client: YouTubeApiClient):
        result = client.get_video_details([])
        assert result == []

    def test_returns_empty_on_exception(self, client: YouTubeApiClient, mock_service: MagicMock):
        mock_service.videos().list().execute.side_effect = Exception("API error")

        result = client.get_video_details(["vid_001"])

        assert result == []


class TestParseDuration:
    @pytest.mark.parametrize("raw,expected", [
        ("PT10M30S", 630),
        ("PT1H2M3S", 3723),
        ("PT30S", 30),
        ("PT5M", 300),
        ("PT1H", 3600),
        ("PT0S", None),
        (None, None),
        ("", None),
        ("INVALID", None),
    ])
    def test_parse_duration(self, raw, expected):
        assert YouTubeApiClient._parse_duration(raw) == expected


class TestBestThumbnail:
    def test_picks_maxres_first(self):
        thumbs = {
            "default": {"url": "http://default"},
            "high": {"url": "http://high"},
            "maxres": {"url": "http://maxres"},
        }
        assert YouTubeApiClient._best_thumbnail(thumbs) == "http://maxres"

    def test_falls_back_to_high(self):
        thumbs = {"high": {"url": "http://high"}, "default": {"url": "http://default"}}
        assert YouTubeApiClient._best_thumbnail(thumbs) == "http://high"

    def test_returns_none_for_empty(self):
        assert YouTubeApiClient._best_thumbnail({}) is None
