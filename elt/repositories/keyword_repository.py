from __future__ import annotations

from google.cloud import bigquery

from elt.datacontext.models.keyword_dto import KeywordDTO


class KeywordRepository:
    def __init__(self, client: bigquery.Client, project_id: str, dataset: str) -> None:
        self._client = client
        self._project_id = project_id
        self._dataset = dataset

    def _table(self, name: str) -> str:
        return f"`{self._project_id}.{self._dataset}.{name}`"

    def get_active_keywords(self) -> list[KeywordDTO]:
        query = f"""
            SELECT keyword_id, keyword_text, search_cluster, needs_backfill
            FROM {self._table("keyword_config")}
            WHERE is_active = TRUE
            ORDER BY search_cluster, keyword_text
        """
        rows = self._client.query(query).result()
        return [
            KeywordDTO(
                keyword_id=row.keyword_id,
                keyword_text=row.keyword_text,
                search_cluster=row.search_cluster,
                needs_backfill=bool(row.needs_backfill) if row.needs_backfill is not None else False,
            )
            for row in rows
        ]

    def clear_needs_backfill(self, keyword_ids: list[str]) -> None:
        if not keyword_ids:
            return
        query = f"""
            UPDATE {self._table("keyword_config")}
            SET needs_backfill = FALSE
            WHERE keyword_id IN UNNEST(@keyword_ids)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("keyword_ids", "STRING", keyword_ids)
            ]
        )
        self._client.query(query, job_config=job_config).result()