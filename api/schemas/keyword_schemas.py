from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class KeywordCreateRequest(BaseModel):
    keyword_text: str
    search_cluster: Optional[str] = None

class KeywordUpdateRequest(BaseModel):
    keyword_text: Optional[str] = None
    search_cluster: Optional[str] = None

class KeywordResponse(BaseModel):
    keyword_id: str
    keyword_text: str
    search_cluster: Optional[str] = None
    is_active: bool
    needs_backfill: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class KeywordSuggestionResponse(BaseModel):
    keyword_id: str
    keyword_text: str
    search_cluster: Optional[str] = None
    match_reason: Optional[str] = None
    similarity_score: Optional[int] = None

class KeywordBulkLinkRequest(BaseModel):
    keyword_ids: List[str]
    product_id: str
