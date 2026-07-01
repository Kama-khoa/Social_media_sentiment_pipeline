from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from api.dependencies import require_admin
from api.bq_client import get_bq_client
from api.schemas.keyword_schemas import (
    KeywordCreateRequest,
    KeywordUpdateRequest,
    KeywordBulkLinkRequest,
    KeywordResponse,
    KeywordSuggestionResponse,
)
from api.services.keyword_service import KeywordService
from api.config import get_settings

router = APIRouter(prefix="/admin/keywords", tags=["admin-keywords"])

def get_keyword_service(bq_client = Depends(get_bq_client)) -> KeywordService:
    settings = get_settings()
    return KeywordService(bq_client=bq_client, project_id=settings.gcp_project_id, dataset=settings.bq_dataset)

@router.get("", response_model=List[KeywordResponse])
def list_keywords(
    product_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    return service.list_keywords(product_id=product_id, is_active=is_active, limit=limit, offset=offset)

@router.post("", response_model=KeywordResponse, status_code=201)
def create_keyword(
    req: KeywordCreateRequest,
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    return service.create_keyword(req)

@router.put("/{keyword_id}", response_model=KeywordResponse)
def update_keyword(
    keyword_id: str,
    req: KeywordUpdateRequest,
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    try:
        return service.update_keyword(keyword_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{keyword_id}", status_code=204)
def delete_keyword(
    keyword_id: str,
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    service.deactivate_keyword(keyword_id)
    return None

@router.post("/suggest", response_model=List[KeywordSuggestionResponse])
def suggest_keywords(
    payload: dict,
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    product_id = payload.get("product_id")
    if not product_id:
        raise HTTPException(status_code=400, detail="Missing product_id")
        
    try:
        return service.generate_suggestions(product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/bulk-link", response_model=dict)
def bulk_link_keywords(
    req: KeywordBulkLinkRequest,
    admin=Depends(require_admin),
    service: KeywordService = Depends(get_keyword_service),
):
    return service.bulk_link(req)
