from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.cloud import bigquery

from elt.datacontext.models.comment_dto import CommentDTO


class ApiCommentRepository:
    def __init__(self, client: bigquery.Client, project_id: str, dataset: str) -> None:
        self._client = client
        self._project_id = project_id
        self._dataset = dataset

    def _table(self, name: str) -> str:
        return f"`{self._project_id}.{self._dataset}.{name}`"

    def merge_comments(self, comments: list[CommentDTO]) -> int:
        if not comments:
            return 0

        comments_by_id = {comment.comment_id: comment for comment in comments}
        comments = list(comments_by_id.values())
        temp_name = f"_tmp_api_comments_{uuid.uuid4().hex}"
        temp_table_id = f"{self._project_id}.{self._dataset}.{temp_name}"
        rows = [comment.to_dict() for comment in comments]

        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("parent_comment_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("author_channel_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("author_display_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("text_original", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("text_display", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("like_count", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("reply_count", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("is_reply", "BOOL", mode="REQUIRED"),
                bigquery.SchemaField("crawl_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("crawled_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("gcs_partition_date", "STRING", mode="REQUIRED"),
            ],
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        self._client.load_table_from_json(rows, temp_table_id, job_config=job_config).result()
        try:
            query = f"""
                MERGE {self._table("raw_comments_api")} AS target
                USING {self._table(temp_name)} AS source
                ON target.comment_id = source.comment_id
                WHEN MATCHED THEN UPDATE SET
                    video_id = source.video_id,
                    channel_id = source.channel_id,
                    parent_comment_id = source.parent_comment_id,
                    author_channel_id = source.author_channel_id,
                    author_display_name = source.author_display_name,
                    text_original = source.text_original,
                    text_display = source.text_display,
                    like_count = source.like_count,
                    reply_count = source.reply_count,
                    is_reply = source.is_reply,
                    crawl_type = source.crawl_type,
                    published_at = source.published_at,
                    updated_at = source.updated_at,
                    crawled_at = source.crawled_at,
                    gcs_partition_date = source.gcs_partition_date
                WHEN NOT MATCHED THEN INSERT (
                    comment_id, video_id, channel_id, parent_comment_id,
                    author_channel_id, author_display_name, text_original,
                    text_display, like_count, reply_count, is_reply, crawl_type,
                    published_at, updated_at, crawled_at, gcs_partition_date
                ) VALUES (
                    source.comment_id, source.video_id, source.channel_id,
                    source.parent_comment_id, source.author_channel_id,
                    source.author_display_name, source.text_original,
                    source.text_display, source.like_count, source.reply_count,
                    source.is_reply, source.crawl_type, source.published_at,
                    source.updated_at, source.crawled_at, source.gcs_partition_date
                )
            """
            self._client.query(query).result()
            return len(comments)
        finally:
            self._client.delete_table(temp_table_id, not_found_ok=True)

    def get_existing_comment_ids(self, video_id: str) -> set[str]:
        query = f"""
            SELECT comment_id
            FROM {self._table("raw_comments_api")}
            WHERE video_id = @video_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            ]
        )
        return {
            row.comment_id
            for row in self._client.query(query, job_config=job_config).result()
        }

    def get_candidate_videos(self, limit: int) -> list[dict]:
        query = f"""
            SELECT
                v.video_id,
                v.channel_id,
                v.title,
                v.published_at,
                COALESCE(v.comment_count, 0) AS comment_count,
                COALESCE(v.view_count, 0) AS view_count,
                s.status,
                s.comments_collected,
                s.pages_crawled,
                s.quota_units_used,
                s.last_page_token
            FROM `{self._project_id}.{self._dataset}_staging.stg_youtube_videos` v
            JOIN `{self._project_id}.{self._dataset}_intermediate.int_video_product_mentions` m
              ON v.video_id = m.video_id
            LEFT JOIN {self._table("api_comment_backfill_state")} s
              ON v.video_id = s.video_id
            WHERE COALESCE(v.comment_count, 0) > 0
              AND COALESCE(s.status, '') NOT IN ('done', 'no_comments', 'comments_disabled')
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY v.video_id
                ORDER BY m.confidence_score DESC
            ) = 1
            ORDER BY published_at DESC, comment_count DESC, view_count DESC
            LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )
        return [dict(row) for row in self._client.query(query, job_config=job_config).result()]

    def update_backfill_state(
        self,
        video_id: str,
        channel_id: str | None,
        status: str,
        comments_collected: int,
        pages_crawled: int,
        quota_units_used: int,
        last_page_token: str | None = None,
        last_error: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        query = f"""
            MERGE {self._table("api_comment_backfill_state")} AS target
            USING (
                SELECT
                    @video_id AS video_id,
                    @channel_id AS channel_id,
                    @status AS status,
                    @comments_collected AS comments_collected,
                    @pages_crawled AS pages_crawled,
                    @quota_units_used AS quota_units_used,
                    @last_page_token AS last_page_token,
                    @last_error AS last_error,
                    @now AS last_crawled_at,
                    @now AS updated_at
            ) AS source
            ON target.video_id = source.video_id
            WHEN MATCHED THEN UPDATE SET
                channel_id = source.channel_id,
                status = source.status,
                comments_collected = source.comments_collected,
                pages_crawled = source.pages_crawled,
                quota_units_used = source.quota_units_used,
                last_page_token = source.last_page_token,
                last_error = source.last_error,
                last_crawled_at = source.last_crawled_at,
                updated_at = source.updated_at
            WHEN NOT MATCHED THEN INSERT (
                video_id, channel_id, status, comments_collected, pages_crawled,
                quota_units_used, last_page_token, last_error, last_crawled_at, updated_at
            ) VALUES (
                source.video_id, source.channel_id, source.status,
                source.comments_collected, source.pages_crawled,
                source.quota_units_used, source.last_page_token, source.last_error,
                source.last_crawled_at, source.updated_at
            )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
                bigquery.ScalarQueryParameter("channel_id", "STRING", channel_id),
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("comments_collected", "INT64", comments_collected),
                bigquery.ScalarQueryParameter("pages_crawled", "INT64", pages_crawled),
                bigquery.ScalarQueryParameter("quota_units_used", "INT64", quota_units_used),
                bigquery.ScalarQueryParameter("last_page_token", "STRING", last_page_token),
                bigquery.ScalarQueryParameter("last_error", "STRING", last_error),
                bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
            ]
        )
        self._client.query(query, job_config=job_config).result()
