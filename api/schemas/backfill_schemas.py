from pydantic import BaseModel, Field
from typing import Optional

class HistoricalBackfillRequest(BaseModel):
    limit_channels: int = Field(default=5, ge=1, le=50)

class BackfillStatusResponse(BaseModel):
    is_running: bool
    current_dag_run_id: Optional[str] = None
    channels_remaining: int
    total_channels: int
