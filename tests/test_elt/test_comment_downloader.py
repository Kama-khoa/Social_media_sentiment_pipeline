from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from elt.datacontext.models.comment_dto import CommentDTO
from elt.extract.helpers.comment_downloader import CommentDownloader, ProxyConfig

RAW_COMMENTS = [
    {
        "cid": "UgxABC123",
        "text": "Pin trâu lắm, dùng cả ngày không hết",
        "author": "Nguyen Van A",
        "channel": "UCuser_a",
        "votes": 42,
        "replies": 3,
        "reply": False,
        "time_parsed": 1741824000.0,
    },
    {
        "cid": "UgxABC123.UgxDEF456",
        "text": "Đồng ý, pin rất tốt",
        "author": "Tran Van B",
        "channel": "UCuser_b",
        "votes": 5,
        "replies": 0,
        "reply": True,
        "time_parsed": 1741910400.0,
    },
    {
        "cid": "",
        "text": "Missing cid",
        "author": "Ghost",
        "votes": 0,
        "replies": 0,
        "reply": False,
        "time_parsed": None,
    },
    {
        "cid": "UgxGHI789",
        "text": "",
        "author": "Empty text",
        "votes": 0,
        "replies": 0,
        "reply": False,
        "time_parsed": None,
    },
]


class TestProxyConfig:
    def test_to_proxy_url(self):
        cfg = ProxyConfig(host="proxy.example.com", port=22225, username="user", password="pass")
        assert cfg.to_proxy_url() == "http://user:pass@proxy.example.com:22225"


class TestDownload:
    @patch("elt.extract.helpers.comment_downloader.YoutubeCommentDownloader")
    def test_download_limits_results(self, mock_cls: MagicMock):
        mock_downloader = MagicMock()
        mock_downloader.get_comments_from_url.return_value = iter(RAW_COMMENTS)
        mock_cls.return_value = mock_downloader

        dl = CommentDownloader()
        result = dl.download("vid_test", max_comments=2)

        assert len(result) == 2

    @patch("elt.extract.helpers.comment_downloader.YoutubeCommentDownloader")
    def test_download_returns_empty_on_exception(self, mock_cls: MagicMock):
        mock_downloader = MagicMock()
        mock_downloader.get_comments_from_url.side_effect = Exception("blocked")
        mock_cls.return_value = mock_downloader

        dl = CommentDownloader()
        result = dl.download("vid_bad")

        assert result == []

    def test_download_uses_clean_session_for_comment_downloader(self):
        dl = CommentDownloader()

        with patch.object(
            dl,
            "_download_once",
            return_value=[{"cid": "ok"}],
        ) as mock_download:
            result = dl.download("vid_cookie")

        assert result == [{"cid": "ok"}]
        assert mock_download.call_args_list[0].kwargs == {
            "proxy": None,
        }

    def test_download_treats_empty_comments_as_proxy_fallback(self):
        proxy = ProxyConfig(host="proxy.example.com", port=22225, username="user", password="pass")
        dl = CommentDownloader(proxy_config=proxy)

        with patch.object(
            dl,
            "_download_once",
            side_effect=[[], [{"cid": "proxy_ok"}]],
        ) as mock_download:
            result = dl.download("vid_empty_first")

        assert result == [{"cid": "proxy_ok"}]
        assert mock_download.call_args_list[0].kwargs["proxy"] is None
        assert mock_download.call_args_list[1].kwargs["proxy"] == proxy.to_proxy_url()

    def test_download_returns_empty_without_proxy_when_clean_session_empty(self):
        dl = CommentDownloader()

        with patch.object(
            dl,
            "_download_once",
            return_value=[],
        ) as mock_download:
            result = dl.download("vid_empty_first")

        assert result == []
        assert len(mock_download.call_args_list) == 1

    def test_download_uses_proxy_last_without_cookies(self):
        proxy = ProxyConfig(host="proxy.example.com", port=22225, username="user", password="pass")
        dl = CommentDownloader(proxy_config=proxy)

        with patch.object(
            dl,
            "_download_once",
            side_effect=[None, [{"cid": "proxy_ok"}]],
        ) as mock_download:
            result = dl.download("vid_proxy")

        assert result == [{"cid": "proxy_ok"}]
        assert mock_download.call_args_list[1].kwargs["proxy"] == proxy.to_proxy_url()


class TestToCommentDtos:
    def test_converts_valid_comments(self):
        dl = CommentDownloader()
        dtos = dl.to_comment_dtos(RAW_COMMENTS, video_id="vid_test", channel_id="UC_ch")

        assert len(dtos) == 2

        top_level = dtos[0]
        assert isinstance(top_level, CommentDTO)
        assert top_level.comment_id == "UgxABC123"
        assert top_level.video_id == "vid_test"
        assert top_level.channel_id == "UC_ch"
        assert top_level.text_original == "Pin trâu lắm, dùng cả ngày không hết"
        assert top_level.is_reply is False
        assert top_level.parent_comment_id is None
        assert top_level.like_count == 42
        assert top_level.reply_count == 3
        assert top_level.crawl_type == "full"
        assert top_level.published_at is not None

        reply = dtos[1]
        assert reply.is_reply is True
        assert reply.parent_comment_id == "UgxABC123"
        assert reply.comment_id == "UgxABC123.UgxDEF456"

    def test_cleans_comment_text_and_keeps_raw_display(self):
        dl = CommentDownloader()
        raw_text = "Samsung hay bị chảy mực lắm đó :)))"
        dtos = dl.to_comment_dtos(
            [{"cid": "c1", "text": raw_text, "reply": False}],
            "vid",
            "ch",
        )

        assert len(dtos) == 1
        assert dtos[0].text_original == "Samsung hay bị chảy mực lắm đó cam_xuc_cuoi"
        assert dtos[0].text_display == raw_text

    def test_cleans_timestamp_and_multiple_emoticons(self):
        dl = CommentDownloader()
        raw_text = "Bây giờ tui vẫn chưa xem endgame :((((\n6:33 con kiu :))"
        dtos = dl.to_comment_dtos(
            [{"cid": "c1", "text": raw_text, "reply": False}],
            "vid",
            "ch",
        )

        assert len(dtos) == 1
        assert (
            dtos[0].text_original
            == "Bây giờ tui vẫn chưa xem endgame cam_xuc_buon con kiu cam_xuc_cuoi"
        )
        assert dtos[0].text_display == raw_text

    def test_removes_noise_while_preserving_vietnamese_text(self):
        dl = CommentDownloader()
        raw_text = (
            "@abc Máy đẹp quá 😂🔥 xem thêm https://example.com?a=1 "
            "#iphone pin trâu &amp; màn hình ổn!"
        )
        dtos = dl.to_comment_dtos(
            [{"cid": "c1", "text": raw_text, "reply": False}],
            "vid",
            "ch",
        )

        assert len(dtos) == 1
        assert dtos[0].text_original == "Máy đẹp quá xem thêm pin trâu màn hình ổn!"

    def test_skips_comment_when_clean_text_is_empty(self):
        dl = CommentDownloader()
        raw = [{"cid": "valid_cid", "text": "😂🔥 #tag @user https://example.com"}]
        dtos = dl.to_comment_dtos(raw, "vid", "ch")
        assert len(dtos) == 0

    def test_skips_empty_cid(self):
        dl = CommentDownloader()
        raw = [{"cid": "", "text": "has text"}]
        dtos = dl.to_comment_dtos(raw, "vid", "ch")
        assert len(dtos) == 0

    def test_skips_empty_text(self):
        dl = CommentDownloader()
        raw = [{"cid": "valid_cid", "text": ""}]
        dtos = dl.to_comment_dtos(raw, "vid", "ch")
        assert len(dtos) == 0

    def test_handles_none_time_parsed(self):
        dl = CommentDownloader()
        raw = [{"cid": "c1", "text": "hello", "time_parsed": None, "reply": False}]
        dtos = dl.to_comment_dtos(raw, "vid", "ch")
        assert len(dtos) == 1
        assert dtos[0].published_at is None


class TestSafeInt:
    @pytest.mark.parametrize("val,expected", [
        (42, 42),
        ("100", 100),
        (None, 0),
        ("abc", 0),
        (0, 0),
    ])
    def test_safe_int(self, val, expected):
        assert CommentDownloader._safe_int(val) == expected


class TestParseTime:
    def test_valid_timestamp(self):
        result = CommentDownloader._parse_time(1741824000.0)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_none(self):
        assert CommentDownloader._parse_time(None) is None

    def test_invalid_string(self):
        assert CommentDownloader._parse_time("not_a_number") is None
