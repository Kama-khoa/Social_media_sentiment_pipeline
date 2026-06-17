from google.cloud import bigquery
from typing import List
from api.schemas.channel_suggestion_schemas import ChannelSuggestionResponse, ChannelApproveRequest

class ChannelSuggestionService:
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset: str):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset = dataset
        self.table_ref = f"{project_id}.{dataset}.channel_config"

    def get_suggestions(self, min_video_count: int = 2, limit: int = 20) -> List[ChannelSuggestionResponse]:
        return []

    def approve_suggestion(self, req: ChannelApproveRequest):
        query = f"""
            INSERT INTO `{self.table_ref}` (channel_id, channel_name, channel_url, channel_handle, is_active, created_at)
            VALUES (@channel_id, @channel_name, @channel_url, @channel_handle, TRUE, CURRENT_TIMESTAMP())
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("channel_id", "STRING", req.channel_id),
            bigquery.ScalarQueryParameter("channel_name", "STRING", req.channel_name),
            bigquery.ScalarQueryParameter("channel_url", "STRING", req.channel_url),
            bigquery.ScalarQueryParameter("channel_handle", "STRING", req.channel_handle),
        ])
        self.bq_client.query(query, job_config=job_config).result()
