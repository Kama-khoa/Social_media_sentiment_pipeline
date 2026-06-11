from __future__ import annotations

import html
import itertools
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import requests
from youtube_comment_downloader import YoutubeCommentDownloader

from elt.datacontext.models.comment_dto import CommentDTO
from elt.extract.helpers.ytdlp_session_pool import YtdlpRateLimitError

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 20

_RATE_LIMIT_PHRASES = [
    "http error 429",
    "too many requests",
    "rate limit",
    "rate-limit",
    "temporarily blocked",
    "sign in to confirm",
    "confirm you're not a bot",
]

_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"(?<!\w)(?:\d{1,2}:)?\d{1,2}:\d{2}(?!\w)")
_LAUGH_EMOTICON_RE = re.compile(r"(?<!\w)(?::-?\)+|=\)+|:-?D|=D)(?!\w)", re.IGNORECASE)
_SAD_EMOTICON_RE = re.compile(r"(?<!\w)(?::-?\(+|T_T|;_;)(?!\w)", re.IGNORECASE)
_MENTION_RE = re.compile(r"(?<!\w)@[\w.\-]+", re.UNICODE)
_HASHTAG_RE = re.compile(r"(?<!\w)#[\w_]+", re.UNICODE)
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_WHITESPACE_RE = re.compile(r"\s+")
_ALLOWED_PUNCTUATION = set(".,!?:;_")


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str

    def to_proxy_url(self) -> str:
        username = quote(self.username, safe="")
        password = quote(self.password, safe="")
        return f"http://{username}:{password}@{self.host}:{self.port}"


class CommentDownloader:

    def __init__(
        self,
        proxy_config: Optional[ProxyConfig] = None,
    ) -> None:
        self._proxy_config = proxy_config
        self._last_logged_session: str | None = None

    def download(self, video_id: str, max_comments: int = 500) -> list[dict]:
        try:
            comments = self.download_clean(video_id, max_comments)
        except YtdlpRateLimitError:
            logger.warning("Comment clean session was rate-limited for video_id=%s", video_id)
            comments = []
        if comments:
            return comments

        proxy = self._proxy_config.to_proxy_url() if self._proxy_config else None
        if not proxy:
            return []

        try:
            return self.download_with_proxy(video_id, max_comments)
        except YtdlpRateLimitError:
            logger.warning("Comment proxy fallback was rate-limited for video_id=%s", video_id)
            return []

    def download_clean(
        self,
        video_id: str,
        max_comments: int,
    ) -> list[dict] | None:
        self._log_session("clean-session")
        return self._download_once(
            video_id,
            max_comments,
            proxy=None,
        )

    def download_with_proxy(
        self,
        video_id: str,
        max_comments: int,
    ) -> list[dict]:
        proxy = self._proxy_config.to_proxy_url() if self._proxy_config else None
        if not proxy:
            return []

        self._log_session(None, proxy_fallback=True)
        comments = self._download_once(
            video_id,
            max_comments,
            proxy=proxy,
        )
        if comments:
            return comments
        logger.info("Comment proxy fallback returned no comments for video_id=%s", video_id)
        return []

    def _log_session(
        self,
        label: str | None,
        proxy_fallback: bool = False,
    ) -> None:
        if proxy_fallback:
            label = "proxy-fallback-no-cookies"

        if label == self._last_logged_session:
            return

        self._last_logged_session = label
        if proxy_fallback:
            logger.warning("Comment downloader switched to %s", label)
        else:
            logger.info("Comment downloader using %s", label)

    def _download_once(
        self,
        video_id: str,
        max_comments: int,
        proxy: str | None,
    ) -> list[dict] | None:
        downloader = YoutubeCommentDownloader()
        self._install_timeout(downloader.session)
        if proxy:
            downloader.session.proxies.update({
                "http": proxy,
                "https": proxy,
            })

        try:
            generator = downloader.get_comments_from_url(
                f"https://www.youtube.com/watch?v={video_id}",
                sort_by=0,
            )
            comments = list(itertools.islice(generator, max_comments))
        except Exception as exc:
            logger.exception(
                "Comment download failed for video_id=%s proxy_enabled=%s",
                video_id,
                bool(proxy),
            )
            if proxy and isinstance(exc, requests.exceptions.ProxyError):
                return None
            if self._is_rate_limited(exc):
                raise YtdlpRateLimitError(video_id) from exc
            return None

        return comments

    @staticmethod
    def _install_timeout(session: requests.Session) -> None:
        original_request = session.request

        def request_with_timeout(method, url, **kwargs):
            kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
            return original_request(method, url, **kwargs)

        session.request = request_with_timeout

    @staticmethod
    def _is_rate_limited(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(phrase in message for phrase in _RATE_LIMIT_PHRASES)

    def to_comment_dtos(
        self,
        raw_comments: list[dict],
        video_id: str,
        channel_id: str,
    ) -> list[CommentDTO]:
        now = datetime.now(timezone.utc)
        dtos: list[CommentDTO] = []
        for raw in raw_comments:
            cid = raw.get("cid")
            raw_text = raw.get("text")
            if not cid or not raw_text:
                continue

            cleaned_text = self._clean_comment_text(str(raw_text))
            if not cleaned_text:
                continue

            is_reply = bool(raw.get("reply", False))
            parent_id = None
            if is_reply and "." in cid:
                parent_id = cid.split(".")[0]

            published_at = self._parse_time(raw.get("time_parsed"))

            dtos.append(CommentDTO(
                comment_id=cid,
                video_id=video_id,
                channel_id=channel_id,
                text_original=cleaned_text,
                is_reply=is_reply,
                crawl_type="full",
                crawled_at=now,
                parent_comment_id=parent_id,
                author_channel_id=raw.get("channel"),
                author_display_name=raw.get("author"),
                text_display=str(raw_text),
                like_count=self._safe_int(raw.get("votes", 0)),
                reply_count=self._safe_int(raw.get("replies", 0)),
                published_at=published_at,
                updated_at=published_at,
            ))
        return dtos

    @staticmethod
    def _clean_comment_text(text: str) -> str:
        cleaned = html.unescape(text)
        cleaned = unicodedata.normalize("NFKC", cleaned)
        cleaned = _ZERO_WIDTH_RE.sub(" ", cleaned)
        cleaned = _URL_RE.sub(" ", cleaned)
        cleaned = _TIMESTAMP_RE.sub(" ", cleaned)
        cleaned = _LAUGH_EMOTICON_RE.sub(" cam_xuc_cuoi ", cleaned)
        cleaned = _SAD_EMOTICON_RE.sub(" cam_xuc_buon ", cleaned)
        cleaned = _MENTION_RE.sub(" ", cleaned)
        cleaned = _HASHTAG_RE.sub(" ", cleaned)

        chars: list[str] = []
        for char in cleaned:
            category = unicodedata.category(char)
            if category.startswith("C"):
                chars.append(" ")
            elif category.startswith("S"):
                chars.append(" ")
            elif category.startswith("P") and char not in _ALLOWED_PUNCTUATION:
                chars.append(" ")
            else:
                chars.append(char)

        return _WHITESPACE_RE.sub(" ", "".join(chars)).strip()

    @staticmethod
    def _parse_time(val) -> datetime | None:
        if val is None:
            return None
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            return None

    @staticmethod
    def _safe_int(val) -> int:
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
