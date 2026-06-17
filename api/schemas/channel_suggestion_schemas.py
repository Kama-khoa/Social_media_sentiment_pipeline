from pydantic import BaseModel
from typing import Optional

class ChannelSuggestionResponse(BaseModel):
    channel_id: str
    channel_name: str
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: int
    match_score: float

class ChannelApproveRequest(BaseModel):
    channel_id: str
    channel_name: str
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
