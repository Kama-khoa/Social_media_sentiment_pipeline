from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_RSS_URL_TEMPLATE = (
    "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
)


class RssFeedReader:

    def fetch_feed(self, channel_id: str) -> list[dict]:
        url = _RSS_URL_TEMPLATE.format(channel_id=channel_id)
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning("RSS parse error for channel %s: %s", channel_id, feed.bozo_exception)
            return []

        entries: list[dict] = []
        for entry in feed.entries:
            video_id = self._extract_video_id(entry)
            if not video_id:
                continue
            published = self._parse_published(entry)
            entries.append({
                "video_id": video_id,
                "title": entry.get("title", ""),
                "published_at": published,
                "link": entry.get("link", ""),
            })
        return entries

    def filter_by_date(
        self,
        entries: list[dict],
        after: datetime,
    ) -> list[dict]:
        after_utc = after.astimezone(timezone.utc) if after.tzinfo else after.replace(tzinfo=timezone.utc)
        return [
            e for e in entries
            if e.get("published_at") is not None and e["published_at"] >= after_utc
        ]

    @staticmethod
    def _extract_video_id(entry) -> str | None:
        yt_id = entry.get("yt_videoid")
        if yt_id:
            return yt_id
        link = entry.get("link", "")
        if "watch?v=" in link:
            return link.split("watch?v=")[-1].split("&")[0]
        return None

    @staticmethod
    def _parse_published(entry) -> datetime | None:
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            try:
                return datetime.fromtimestamp(mktime(published_parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                pass

        published_str = entry.get("published")
        if published_str:
            for fmt in ("%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(published_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        return None