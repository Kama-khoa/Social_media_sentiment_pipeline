from __future__ import annotations

from datetime import datetime, timezone
from time import struct_time
from unittest.mock import MagicMock, patch

import pytest

from elt.extract.helpers.rss_feed_reader import RssFeedReader


def _make_entry(video_id: str, title: str, published_str: str, published_parsed: struct_time | None = None) -> MagicMock:
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "yt_videoid": video_id,
        "title": title,
        "link": f"https://www.youtube.com/watch?v={video_id}",
        "published": published_str,
    }.get(key, default)
    entry.__getitem__ = entry.get
    if published_parsed:
        entry.get = lambda key, default=None: {
            "yt_videoid": video_id,
            "title": title,
            "link": f"https://www.youtube.com/watch?v={video_id}",
            "published": published_str,
            "published_parsed": published_parsed,
        }.get(key, default)
    return entry


@pytest.fixture
def reader() -> RssFeedReader:
    return RssFeedReader()


class TestFetchFeed:
    @patch("elt.extract.helpers.rss_feed_reader.feedparser.parse")
    def test_parses_entries(self, mock_parse: MagicMock, reader: RssFeedReader):
        entry1 = _make_entry("vid_A", "Review Samsung", "2026-03-15T08:00:00+00:00")
        entry2 = _make_entry("vid_B", "Test iPhone", "2026-03-14T10:00:00+00:00")

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [entry1, entry2]
        mock_parse.return_value = mock_feed

        result = reader.fetch_feed("UC_test_channel_id")

        assert len(result) == 2
        assert result[0]["video_id"] == "vid_A"
        assert result[1]["video_id"] == "vid_B"
        mock_parse.assert_called_once_with(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC_test_channel_id"
        )

    @patch("elt.extract.helpers.rss_feed_reader.feedparser.parse")
    def test_returns_empty_on_bozo_no_entries(self, mock_parse: MagicMock, reader: RssFeedReader):
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("parse error")
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        result = reader.fetch_feed("UC_bad")

        assert result == []


class TestFilterByDate:
    def test_filters_after_date(self, reader: RssFeedReader):
        entries = [
            {"video_id": "v1", "published_at": datetime(2026, 3, 15, tzinfo=timezone.utc)},
            {"video_id": "v2", "published_at": datetime(2026, 3, 10, tzinfo=timezone.utc)},
            {"video_id": "v3", "published_at": datetime(2026, 3, 14, tzinfo=timezone.utc)},
        ]
        after = datetime(2026, 3, 13, tzinfo=timezone.utc)

        result = reader.filter_by_date(entries, after)

        ids = [e["video_id"] for e in result]
        assert "v1" in ids
        assert "v3" in ids
        assert "v2" not in ids

    def test_handles_none_published_at(self, reader: RssFeedReader):
        entries = [
            {"video_id": "v1", "published_at": None},
            {"video_id": "v2", "published_at": datetime(2026, 3, 15, tzinfo=timezone.utc)},
        ]
        after = datetime(2026, 3, 14, tzinfo=timezone.utc)

        result = reader.filter_by_date(entries, after)

        assert len(result) == 1
        assert result[0]["video_id"] == "v2"

    def test_empty_list(self, reader: RssFeedReader):
        result = reader.filter_by_date([], datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert result == []
