from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from google.cloud import bigquery


class QuotaRepository:
    def __init__(self, client: bigquery.Client, project_id: str, dataset: str) -> None:
        self._client = client
        self._project_id = project_id
        self._dataset = dataset

    def _table(self, name: str) -> str:
        return f"`{self._project_id}.{self._dataset}.{name}`"

    def log_operation(
        self,
        operation_type: str,
        bucket: str,
        units_used: int,
        dag_run_id: str,
        videos_processed: int = 0,
        comments_collected: int = 0,
        execution_time_seconds: float | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        row = {
            "log_id": str(uuid.uuid4()),
            "log_date": now.date().isoformat(),
            "dag_run_id": dag_run_id,
            "operation_type": operation_type,
            "bucket": bucket,
            "units_used": units_used,
            "videos_processed": videos_processed,
            "comments_collected": comments_collected,
            "execution_time_seconds": execution_time_seconds,
            "created_at": now.isoformat(),
        }
        self._client.insert_rows_json(
            f"{self._project_id}.{self._dataset}.quota_operation_log", [row]
        )

    def get_today_used_by_bucket(self, today: date) -> dict[str, int]:
        query = f"""
            SELECT bucket, SUM(units_used) AS total
            FROM {self._table("quota_operation_log")}
            WHERE DATE(created_at) = @today
            GROUP BY bucket
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("today", "DATE", today.isoformat())
            ]
        )
        rows = list(self._client.query(query, job_config=job_config).result())
        return {row.bucket: row.total for row in rows}

    def upsert_daily_summary(self, today: date, dag_run_id: str) -> None:
        query = f"""
            MERGE {self._table("quota_daily_summary")} AS target
            USING (
                SELECT
                    @today                                                    AS summary_date,
                    @dag_run_id                                               AS dag_run_id,
                    SUM(CASE WHEN operation_type = 'search_videos'
                             THEN units_used ELSE 0 END)                     AS units_search_list,
                    SUM(CASE WHEN operation_type = 'channel_seed'
                             THEN units_used ELSE 0 END)                     AS units_channel_seed,
                    SUM(CASE WHEN operation_type = 'videos_list'
                             THEN units_used ELSE 0 END)                     AS units_videos_list,
                    SUM(CASE WHEN operation_type = 'comment_threads'
                             THEN units_used ELSE 0 END)                     AS units_comment_threads,
                    SUM(units_used)                                           AS total_units_used,
                    SUM(comments_collected)                                   AS comments_collected,
                    SUM(videos_processed)                                     AS videos_discovered
                FROM {self._table("quota_operation_log")}
                WHERE DATE(created_at) = @today
            ) AS source
            ON target.summary_date = source.summary_date
            WHEN MATCHED THEN UPDATE SET
                target.dag_run_id           = source.dag_run_id,
                target.units_search_list    = source.units_search_list,
                target.units_channel_seed   = source.units_channel_seed,
                target.units_videos_list    = source.units_videos_list,
                target.units_comment_threads = source.units_comment_threads,
                target.total_units_used     = source.total_units_used,
                target.comments_collected   = source.comments_collected,
                target.videos_discovered    = source.videos_discovered,
                target.created_at           = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (
                summary_date, dag_run_id,
                units_search_list, units_channel_seed, units_videos_list,
                units_comment_threads, total_units_used,
                comments_collected, videos_discovered, created_at
            ) VALUES (
                source.summary_date, source.dag_run_id,
                source.units_search_list, source.units_channel_seed,
                source.units_videos_list, source.units_comment_threads,
                source.total_units_used, source.comments_collected,
                source.videos_discovered, CURRENT_TIMESTAMP()
            )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("today", "DATE", today.isoformat()),
                bigquery.ScalarQueryParameter("dag_run_id", "STRING", dag_run_id),
            ]
        )
        self._client.query(query, job_config=job_config).result()
