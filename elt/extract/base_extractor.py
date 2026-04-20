from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from elt.datacontext.models.comment_dto import CommentDTO
from elt.datacontext.models.keyword_dto import KeywordDTO
from elt.datacontext.models.video_dto import VideoDTO


class BaseExtractor(ABC):

    #Mode 0: yt-dlp
    @abstractmethod
    def get_channel_videos_historical(
        self,
        channel_id: str,
        keywords: list[KeywordDTO],
    ) -> list[VideoDTO]:
        ...

    #Mode 1: RSS feed
    @abstractmethod
    def get_channel_rss_videos(
        self,
        channel_id: str,
        published_after: datetime,
    ) -> list[dict]:
        ...

    #Mode 2: Youtube API search.list
    @abstractmethod
    def search_videos_global(
        self,
        keyword: str,
        max_results: int,
    ) -> list[tuple[str, str]]:
        ...

    @abstractmethod
    def get_video_details(
        self,
        video_ids: list[str],
    ) -> list[VideoDTO]:
        ...

    #Youtube comments download
    @abstractmethod
    def download_comments(
        self,
        video_id: str,
        channel_id: str,
        max_comments: int,
    ) -> list[CommentDTO]:
        ...