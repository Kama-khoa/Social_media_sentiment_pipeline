from google.cloud import bigquery
from api.schemas.backfill_schemas import HistoricalBackfillRequest

class BackfillService:
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset: str):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset = dataset

    def trigger_historical_backfill(self, req: HistoricalBackfillRequest) -> dict:
        return {
            "status": "triggered",
            "message": f"Historical backfill triggered for {req.limit_channels} channels"
        }

    def get_status(self) -> dict:
        return {
            "total_channels": 0,
            "scanned_channels": 0,
            "status": "idle"
        }
