from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpVideoFetcher

KEYWORDS = [
    KeywordDTO(keyword_id="kw_001", keyword_text="Samsung Galaxy S25", search_cluster="Samsung Galaxy S25"),
    KeywordDTO(keyword_id="kw_002", keyword_text="iPhone 16", search_cluster="iPhone 16"),
]

FAKE_ENTRIES = [
    {
        "id": "vid_001",
        "title": "Review Samsung Galaxy S25 Ultra chi tiết",
        "description": "Đánh giá sản phẩm mới nhất",
        "upload_date": "20260315",
        "view_count": 100000,
        "duration": 600,
        "thumbnail": "https://img.youtube.com/vi/vid_001/maxresdefault.jpg",
    },
    {
        "id": "vid_002",
        "title": "Top 10 điện thoại 2026",
        "description": "Không liên quan đến keyword nào",
        "upload_date": "20260310",
        "view_count": 50000,
        "duration": 300,
        "thumbnail": None,
    },
    {
        "id": "vid_003",
        "title": "So sánh iPhone 16 vs Samsung",
        "description": "",
        "upload_date": "20260312",
        "view_count": 80000,
        "duration": 450,
        "thumbnail": "https://img.youtube.com/vi/vid_003/maxresdefault.jpg",
    },
]


@pytest.fixture
def fetcher() -> YtdlpVideoFetcher:
    return YtdlpVideoFetcher(KEYWORDS)


class TestFetchChannelVideos:
    @patch("elt.extract.helpers.ytdlp_video_fetcher._make_ydl")
    def test_returns_parsed_entries(self, mock_make_ydl: MagicMock, fetcher: YtdlpVideoFetcher):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"entries": FAKE_ENTRIES}
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_make_ydl.return_value = mock_ydl

        result = fetcher.fetch_channel_videos("https://www.youtube.com/@testchannel")

        assert len(result) == 3
        assert result[0]["id"] == "vid_001"
        assert result[0]["title"] == "Review Samsung Galaxy S25 Ultra chi tiết"

    @patch("elt.extract.helpers.ytdlp_video_fetcher._make_ydl")
    def test_returns_empty_on_exception(self, mock_make_ydl: MagicMock, fetcher: YtdlpVideoFetcher):
        mock_make_ydl.side_effect = Exception("network error")

        result = fetcher.fetch_channel_videos("https://www.youtube.com/@bad")

        assert result == []

    @patch("elt.extract.helpers.ytdlp_video_fetcher._make_ydl")
    def test_returns_empty_when_none_result(self, mock_make_ydl: MagicMock, fetcher: YtdlpVideoFetcher):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = None
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_make_ydl.return_value = mock_ydl

        result = fetcher.fetch_channel_videos("https://www.youtube.com/@empty")

        assert result == []


class TestFilterByKeywords:
    def test_matches_title(self, fetcher: YtdlpVideoFetcher):
        matched = fetcher.filter_by_keywords(FAKE_ENTRIES.copy())

        ids = [v["id"] for v in matched]
        assert "vid_001" in ids
        assert "vid_003" in ids
        assert "vid_002" not in ids

    def test_sets_matched_keyword(self, fetcher: YtdlpVideoFetcher):
        videos = [FAKE_ENTRIES[0].copy()]
        matched = fetcher.filter_by_keywords(videos)

        assert matched[0]["_matched_keyword"] == "Samsung Galaxy S25"

    def test_empty_list(self, fetcher: YtdlpVideoFetcher):
        assert fetcher.filter_by_keywords([]) == []


class TestToVideoDtos:
    def test_converts_to_dtos(self, fetcher: YtdlpVideoFetcher):
        videos = [FAKE_ENTRIES[0].copy()]
        videos[0]["_matched_keyword"] = "Samsung Galaxy S25"

        dtos = fetcher.to_video_dtos(videos, "UC_test_channel")

        assert len(dtos) == 1
        dto = dtos[0]
        assert isinstance(dto, VideoDTO)
        assert dto.video_id == "vid_001"
        assert dto.channel_id == "UC_test_channel"
        assert dto.search_mode == "MODE0"
        assert dto.keyword_matched == "Samsung Galaxy S25"
        assert dto.view_count == 100000

    # def test_skips_invalid_upload_date(self, fetcher: YtdlpVideoFetcher):
    #     videos = [{"id": "vid_bad", "title": "Test", "upload_date": None}]

    #     dtos = fetcher.to_video_dtos(videos, "UC_test")

    #     assert len(dtos) == 0

    # def test_parse_upload_date_format(self):
    #     result = YtdlpVideoFetcher._parse_upload_date("20260315")
    #     assert result is not None
    #     assert result.year == 2026
    #     assert result.month == 3
    #     assert result.day == 15

    # def test_parse_upload_date_invalid(self):
    #     assert YtdlpVideoFetcher._parse_upload_date("invalid") is None
    #     assert YtdlpVideoFetcher._parse_upload_date("") is None
    #     assert YtdlpVideoFetcher._parse_upload_date(None) is None
