from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Admin channel config ──────────────────────────────────────────────────────

class ChannelCreateRequest(BaseModel):
    channel_id: str = Field(min_length=2)
    channel_name: str = Field(min_length=2)
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    subscriber_count: Optional[int] = None


class ChannelUpdateRequest(BaseModel):
    channel_name: Optional[str] = Field(default=None, min_length=2)
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    subscriber_count: Optional[int] = None


# ── Admin keyword config ──────────────────────────────────────────────────────

class KeywordCreateRequest(BaseModel):
    keyword_text: str = Field(min_length=1)
    search_cluster: Optional[str] = None


class KeywordUpdateRequest(BaseModel):
    keyword_text: Optional[str] = Field(default=None, min_length=1)
    search_cluster: Optional[str] = None
