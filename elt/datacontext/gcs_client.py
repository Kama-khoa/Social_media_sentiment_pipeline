from __future__ import annotations

import json
from datetime import datetime
from typing import Union

from google.cloud import storage


class GCSClient:
    _VIDEOS_PREFIX = "raw/videos"
    _COMMENTS_PREFIX = "raw/comments"

    def __init__(self, bucket_name: str, project_id: str) -> None:
        self._bucket_name = bucket_name
        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def upload_json(self, gcs_path: str, data: Union[dict, list]) -> str:
        blob = self._bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False),
            content_type="application/json",
        )
        return f"gs://{self._bucket_name}/{gcs_path}"

    def file_exists(self, gcs_path: str) -> bool:
        return self._bucket.blob(gcs_path).exists()

    def list_files(self, prefix: str) -> list[str]:
        blobs = self._client.list_blobs(self._bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]

    @staticmethod
    def build_videos_path(crawled_at: datetime) -> str:
        date_part = crawled_at.strftime("%Y/%m/%d")
        time_part = crawled_at.strftime("%H%M%S")
        return f"{GCSClient._VIDEOS_PREFIX}/{date_part}/videos_run_{time_part}.json"

    @staticmethod
    def build_comments_path(video_id: str, crawled_at: datetime) -> str:
        date_part = crawled_at.strftime("%Y/%m/%d")
        time_part = crawled_at.strftime("%H%M%S")
        return f"{GCSClient._COMMENTS_PREFIX}/{date_part}/comments_{video_id}_{time_part}.json"