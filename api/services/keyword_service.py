from google.cloud import bigquery
from typing import List, Optional
import uuid
from datetime import datetime
from api.schemas.keyword_schemas import (
    KeywordCreateRequest, KeywordUpdateRequest, KeywordResponse,
    KeywordSuggestionResponse, KeywordBulkLinkRequest
)

class KeywordService:
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset: str):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset = dataset
        self.table_ref = f"{project_id}.{dataset}.keyword_config"

    def list_keywords(self, product_id: Optional[str] = None, is_active: Optional[bool] = None, limit: int = 50, offset: int = 0) -> List[KeywordResponse]:
        query = f"SELECT * FROM `{self.table_ref}` WHERE 1=1"
        params = []
        if product_id is not None:
            query += " AND search_cluster = @product_id"
            params.append(bigquery.ScalarQueryParameter("product_id", "STRING", product_id))
        if is_active is not None:
            query += " AND is_active = @is_active"
            params.append(bigquery.ScalarQueryParameter("is_active", "BOOL", is_active))
        
        query += " ORDER BY created_at DESC LIMIT @limit OFFSET @offset"
        params.extend([
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ])

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = self.bq_client.query(query, job_config=job_config).result()
        return [KeywordResponse(**dict(row)) for row in rows]

    def create_keyword(self, req: KeywordCreateRequest) -> KeywordResponse:
        keyword_id = f"kw_{uuid.uuid4().hex[:8]}"
        query = f"""
            INSERT INTO `{self.table_ref}` (keyword_id, keyword_text, search_cluster, is_active, needs_backfill, created_at)
            VALUES (@keyword_id, @keyword_text, @search_cluster, TRUE, TRUE, CURRENT_TIMESTAMP())
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("keyword_id", "STRING", keyword_id),
            bigquery.ScalarQueryParameter("keyword_text", "STRING", req.keyword_text),
            bigquery.ScalarQueryParameter("search_cluster", "STRING", req.search_cluster),
        ])
        self.bq_client.query(query, job_config=job_config).result()
        
        return self.list_keywords(product_id=req.search_cluster, limit=1)[0]

    def update_keyword(self, keyword_id: str, req: KeywordUpdateRequest) -> KeywordResponse:
        updates = []
        params = [bigquery.ScalarQueryParameter("keyword_id", "STRING", keyword_id)]
        
        if req.keyword_text is not None:
            updates.append("keyword_text = @keyword_text")
            params.append(bigquery.ScalarQueryParameter("keyword_text", "STRING", req.keyword_text))
        if req.search_cluster is not None:
            updates.append("search_cluster = @search_cluster")
            params.append(bigquery.ScalarQueryParameter("search_cluster", "STRING", req.search_cluster))
            
        if not updates:
            raise ValueError("No fields to update")
            

        
        query = f"UPDATE `{self.table_ref}` SET {', '.join(updates)} WHERE keyword_id = @keyword_id"
        self.bq_client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
        
        return KeywordResponse(
            keyword_id=keyword_id,
            keyword_text=req.keyword_text or "Updated",
            search_cluster=req.search_cluster,
            is_active=True,
            created_at=datetime.utcnow()
        )

    def deactivate_keyword(self, keyword_id: str):
        query = f"UPDATE `{self.table_ref}` SET is_active = FALSE WHERE keyword_id = @keyword_id"
        self.bq_client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("keyword_id", "STRING", keyword_id)
        ])).result()

    def deactivate_by_product(self, product_id: str) -> int:
        query = f"UPDATE `{self.table_ref}` SET is_active = FALSE WHERE search_cluster = @product_id AND is_active = TRUE"
        job = self.bq_client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id)
        ]))
        job.result()
        return job.num_dml_affected_rows

    def generate_suggestions(self, product_id: str) -> List[KeywordSuggestionResponse]:
        query = f"""
            SELECT keyword_id, keyword_text, search_cluster 
            FROM `{self.table_ref}` 
            WHERE search_cluster IS NULL AND is_active = TRUE
            LIMIT 50
        """
        rows = self.bq_client.query(query).result()
        return [
            KeywordSuggestionResponse(
                keyword_id=row.keyword_id,
                keyword_text=row.keyword_text,
                search_cluster=row.search_cluster,
                match_reason="Chưa liên kết",
                similarity_score=85
            ) for row in rows
        ]

    def bulk_link(self, req: KeywordBulkLinkRequest) -> dict:
        if not req.keyword_ids:
            return {"linked_count": 0}
            
        query = f"""
            UPDATE `{self.table_ref}` 
            SET search_cluster = @product_id 
            WHERE keyword_id IN UNNEST(@keyword_ids)
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", req.product_id),
            bigquery.ArrayQueryParameter("keyword_ids", "STRING", req.keyword_ids),
        ])
        job = self.bq_client.query(query, job_config=job_config)
        job.result()
        return {"linked_count": job.num_dml_affected_rows}
