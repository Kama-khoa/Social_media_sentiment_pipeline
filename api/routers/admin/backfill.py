from fastapi import APIRouter, Depends
from api.dependencies import require_admin
from api.bq_client import get_bq_client
from api.config import get_settings
from api.services.backfill_service import BackfillService
from api.schemas.backfill_schemas import HistoricalBackfillRequest

router = APIRouter(prefix="/admin/backfill", tags=["admin-backfill"])

def get_backfill_service(bq_client = Depends(get_bq_client)) -> BackfillService:
    settings = get_settings()
    return BackfillService(bq_client, settings.gcp_project_id, settings.bq_dataset)

@router.get("/status")
def get_backfill_status(
    admin = Depends(require_admin),
    service: BackfillService = Depends(get_backfill_service)
):
    return service.get_status()

@router.post("/historical")
def trigger_historical_backfill(
    req: HistoricalBackfillRequest,
    admin = Depends(require_admin),
    service: BackfillService = Depends(get_backfill_service)
):
    return service.trigger_historical_backfill(req)
