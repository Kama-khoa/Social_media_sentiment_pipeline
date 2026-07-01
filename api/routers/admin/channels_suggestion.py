from fastapi import APIRouter, Depends, Query
from typing import List

from api.dependencies import require_admin
from api.bq_client import get_bq_client
from api.schemas.channel_suggestion_schemas import (
    ChannelSuggestionResponse,
    ChannelApproveRequest,
)
from api.services.channel_suggestion_service import ChannelSuggestionService
from api.config import get_settings

router = APIRouter(prefix="/admin/channels/suggestions", tags=["admin-channel-suggestions"])

def get_channel_suggestion_service(bq_client = Depends(get_bq_client)) -> ChannelSuggestionService:
    settings = get_settings()
    return ChannelSuggestionService(bq_client=bq_client, project_id=settings.gcp_project_id, dataset=settings.bq_dataset)

@router.get("", response_model=List[ChannelSuggestionResponse])
def get_channel_suggestions(
    min_video_count: int = Query(2, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin=Depends(require_admin),
    service: ChannelSuggestionService = Depends(get_channel_suggestion_service),
):
    return service.get_suggestions(min_video_count=min_video_count, limit=limit)

@router.post("/approve", status_code=201)
def approve_channel(
    req: ChannelApproveRequest,
    admin=Depends(require_admin),
    service: ChannelSuggestionService = Depends(get_channel_suggestion_service),
):
    return service.approve_channel(req)
