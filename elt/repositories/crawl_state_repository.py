from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.cloud import bigquery

from elt.datacontext.models.video_dto import VideoDTO


class CrawlStateRepository:
    def __init__(self, client: bigquery.Client, project_id: str, dataset: str) -> None:
        self._client = client
        self._project_id = project_id
        self._dataset = dataset

    def _table(self, name: str) -> str:
        return f"`{self._project_id}.{self._dataset}.{name}`"

    def bulk_upsert_from_video_dtos(self, videos: list[VideoDTO]) -> None:
        if not videos:
            return

        rows = [
            {
                "video_id": v.video_id,
                "channel_id": v.channel_id,
                "keyword_matched": v.keyword_matched,
                "search_mode": v.search_mode,
                "published_at": v.published_at.astimezone(timezone.utc).isoformat(),
                "comment_count": v.comment_count,
            }
            for v in videos
        ]

        tmp_table = (
            f"{self._project_id}.{self._dataset}"
            f"._tmp_crawl_state_{uuid.uuid4().hex[:8]}"
        )
        schema = [
            bigquery.SchemaField("video_id", "STRING"),
            bigquery.SchemaField("channel_id", "STRING"),
            bigquery.SchemaField("keyword_matched", "STRING"),
            bigquery.SchemaField("search_mode", "STRING"),
            bigquery.SchemaField("published_at", "TIMESTAMP"),
            bigquery.SchemaField("comment_count", "INT64"),
        ]

        job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
        load_job = self._client.load_table_from_json(rows, tmp_table, job_config=job_config)
        load_job.result()

        merge_sql = f"""
            MERGE {self._table("video_crawl_state")} AS target
            USING `{tmp_table}` AS source
            ON target.video_id = source.video_id
            WHEN NOT MATCHED THEN INSERT (
                video_id, channel_id, keyword_id, search_mode,
                published_at, maturity_stage,
                comment_count, last_comment_count,
                total_comments_crawled, last_comment_crawled_at,
                is_comment_complete, last_page_token,
                crawl_status, created_at, updated_at
            ) VALUES (
                source.video_id,
                source.channel_id,
                (
                    SELECT keyword_id
                    FROM {self._table("keyword_config")}
                    WHERE keyword_text = source.keyword_matched
                    LIMIT 1
                ),
                source.search_mode,
                source.published_at,
                CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), source.published_at, DAY) < 3
                        THEN 'new'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), source.published_at, DAY) < 14
                        THEN 'growing'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), source.published_at, DAY) < 30
                        THEN 'mature'
                    ELSE 'archived'
                END,
                source.comment_count,
                NULL,
                0,
                NULL,
                FALSE,
                NULL,
                'pending',
                CURRENT_TIMESTAMP(),
                CURRENT_TIMESTAMP()
            )
            WHEN MATCHED THEN UPDATE SET
                target.comment_count      = source.comment_count,
                target.last_comment_count = target.comment_count,
                target.maturity_stage     = CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), target.published_at, DAY) < 3
                        THEN 'new'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), target.published_at, DAY) < 14
                        THEN 'growing'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), target.published_at, DAY) < 30
                        THEN 'mature'
                    ELSE 'archived'
                END,
                target.updated_at         = CURRENT_TIMESTAMP()
        """
        self._client.query(merge_sql).result()
        self._client.delete_table(tmp_table, not_found_ok=True)

    def get_all_video_ids(self) -> set[str]:
        query = f"""
            SELECT video_id
            FROM {self._table("video_crawl_state")}
        """
        rows = self._client.query(query).result()
        return {row.video_id for row in rows}

    def get_existing_video_ids(self, channel_id: str) -> set[str]:
        query = f"""
            SELECT video_id
            FROM {self._table("video_crawl_state")}
            WHERE channel_id = @channel_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("channel_id", "STRING", channel_id)
            ]
        )
        rows = self._client.query(query, job_config=job_config).result()
        return {row.video_id for row in rows}

    def get_videos_to_crawl(self) -> list[dict]:
        query = f"""
            SELECT
                video_id,
                channel_id,
                published_at,
                comment_count,
                last_comment_count,
                total_comments_crawled,
                maturity_stage
            FROM {self._table("video_crawl_state")}
            WHERE
                crawl_status != 'skipped'
                AND is_comment_complete = FALSE
                AND (
                    last_comment_crawled_at IS NULL
                    OR (
                        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 3
                        AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_comment_crawled_at, HOUR) >= 24
                    )
                    OR (
                        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) BETWEEN 3 AND 14
                        AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_comment_crawled_at, DAY) >= 3
                    )
                    OR (
                        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) BETWEEN 14 AND 30
                        AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_comment_crawled_at, DAY) >= 7
                    )
                    OR (
                        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) > 30
                        AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_comment_crawled_at, DAY) >= 30
                    )
                )
            ORDER BY
                CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 3
                        THEN 100
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 14
                         AND comment_count > COALESCE(last_comment_count, 0) * 1.2
                        THEN 80
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 14
                        THEN 50
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 30
                        THEN 30
                    ELSE 10
                END DESC,
                published_at DESC
        """
        rows = self._client.query(query).result()
        return [
            {
                "video_id": row.video_id,
                "channel_id": row.channel_id,
                "published_at": row.published_at,
                "comment_count": row.comment_count,
                "total_comments_crawled": row.total_comments_crawled,
                "maturity_stage": row.maturity_stage,
            }
            for row in rows
        ]

    def update_after_comment_crawl(
        self,
        video_id: str,
        comments_crawled_this_run: int,
        crawled_at: datetime,
        max_comments_per_video: int,
    ) -> None:
        query = f"""
            UPDATE {self._table("video_crawl_state")}
            SET
                total_comments_crawled  = total_comments_crawled + @delta,
                last_comment_crawled_at = @crawled_at,
                is_comment_complete     = (total_comments_crawled + @delta >= @max_comments),
                crawl_status            = 'crawled',
                maturity_stage          = CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 3
                        THEN 'new'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 14
                        THEN 'growing'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 30
                        THEN 'mature'
                    ELSE 'archived'
                END,
                updated_at              = CURRENT_TIMESTAMP()
            WHERE video_id = @video_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("delta", "INT64", comments_crawled_this_run),
                bigquery.ScalarQueryParameter(
                    "crawled_at", "TIMESTAMP",
                    crawled_at.astimezone(timezone.utc).isoformat()
                ),
                bigquery.ScalarQueryParameter("max_comments", "INT64", max_comments_per_video),
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            ]
        )
        self._client.query(query, job_config=job_config).result()

    def mark_video_skipped(self, video_id: str) -> None:
        query = f"""
            UPDATE {self._table("video_crawl_state")}
            SET
                crawl_status = 'skipped',
                updated_at   = CURRENT_TIMESTAMP()
            WHERE video_id = @video_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id)
            ]
        )
        self._client.query(query, job_config=job_config).result()