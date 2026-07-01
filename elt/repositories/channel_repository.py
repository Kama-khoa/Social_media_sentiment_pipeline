from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import bigquery

from elt.datacontext.models.channel_dto import ChannelDTO


class ChannelRepository:
    def __init__(self, client: bigquery.Client, project_id: str, dataset: str) -> None:
        self._client = client
        self._project_id = project_id
        self._dataset = dataset

    def _table(self, name: str) -> str:
        return f"`{self._project_id}.{self._dataset}.{name}`"

    def get_active_channels(self) -> list[ChannelDTO]:
        query = f"""
            SELECT
                channel_id, channel_name, channel_url, channel_handle,
                subscriber_count, is_active, is_historically_scanned,
                historical_scan_completed_at, created_at, last_updated_at
            FROM {self._table("channel_config")}
            WHERE is_active = TRUE
            ORDER BY subscriber_count DESC
        """
        rows = self._client.query(query).result()
        return [self._row_to_dto(row) for row in rows]

    def get_unscanned_channels(self, limit: int = 5) -> list[ChannelDTO]:
        query = f"""
            SELECT
                channel_id, channel_name, channel_url, channel_handle,
                subscriber_count, is_active, is_historically_scanned,
                historical_scan_completed_at, created_at, last_updated_at
            FROM {self._table("channel_config")}
            WHERE is_active = TRUE
              AND is_historically_scanned = FALSE
            ORDER BY subscriber_count DESC
            LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
        )
        rows = self._client.query(query, job_config=job_config).result()
        return [self._row_to_dto(row) for row in rows]

    def get_active_channel(self, channel_id: str) -> ChannelDTO | None:
        query = f"""
            SELECT
                channel_id, channel_name, channel_url, channel_handle,
                subscriber_count, is_active, is_historically_scanned,
                historical_scan_completed_at, created_at, last_updated_at
            FROM {self._table("channel_config")}
            WHERE channel_id = @channel_id
              AND is_active = TRUE
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("channel_id", "STRING", channel_id)
            ]
        )
        rows = list(self._client.query(query, job_config=job_config).result())
        return self._row_to_dto(rows[0]) if rows else None

    def mark_historically_scanned(self, channel_id: str) -> None:
        query = f"""
            UPDATE {self._table("channel_config")}
            SET
                is_historically_scanned      = TRUE,
                historical_scan_completed_at = CURRENT_TIMESTAMP(),
                last_updated_at              = CURRENT_TIMESTAMP()
            WHERE channel_id = @channel_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("channel_id", "STRING", channel_id)
            ]
        )
        self._client.query(query, job_config=job_config).result()

    @staticmethod
    def _row_to_dto(row: bigquery.Row) -> ChannelDTO:
        def _to_dt(val) -> datetime | None:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
            return None

        return ChannelDTO(
            channel_id=row.channel_id,
            channel_name=row.channel_name,
            channel_url=row.channel_url,
            channel_handle=row.channel_handle,
            subscriber_count=row.subscriber_count,
            is_active=row.is_active,
            is_historically_scanned=row.is_historically_scanned,
            historical_scan_completed_at=_to_dt(row.historical_scan_completed_at),
            created_at=_to_dt(row.created_at),
            last_updated_at=_to_dt(row.last_updated_at),
        )
