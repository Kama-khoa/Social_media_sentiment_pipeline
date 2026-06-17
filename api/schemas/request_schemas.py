from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2)
    role: Literal["user", "admin"] = "user"


class AdminUserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2)
    role: Optional[Literal["user", "admin"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


# ── Admin channel config ──────────────────────────────────────────────────────

class ChannelCreateRequest(BaseModel):
    channel_url: str = Field(min_length=10)


class ChannelUpdateRequest(BaseModel):
    channel_name: Optional[str] = Field(default=None, min_length=2)
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    subscriber_count: Optional[int] = None
    is_active: Optional[bool] = None


class ChannelCrawlRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=730)
    preferred_mode: Literal["auto", "api", "ytdlp"] = "auto"


# ── Admin keyword config ──────────────────────────────────────────────────────

class KeywordCreateRequest(BaseModel):
    keyword_text: str = Field(min_length=1)
    search_cluster: Optional[str] = None


class KeywordUpdateRequest(BaseModel):
    keyword_text: Optional[str] = Field(default=None, min_length=1)
    search_cluster: Optional[str] = None


# ── Product catalog and moderated details ─────────────────────────────────────

class ProductCreateRequest(BaseModel):
    product_id: Optional[str] = None
    product_name: str = Field(min_length=2)
    brand: Optional[str] = None
    category: Optional[str] = None
    release_year: Optional[int] = None
    specs: Optional[dict[str, Any]] = None


class ProductUpdateRequest(BaseModel):
    product_name: Optional[str] = Field(default=None, min_length=2)
    brand: Optional[str] = None
    category: Optional[str] = None
    release_year: Optional[int] = None
    is_active: Optional[bool] = None


class ProductAliasCreateRequest(BaseModel):
    product_id: str = Field(min_length=1)
    alias_text: str = Field(min_length=2)
    alias_type: str = "common_name"


class ProductSpecTemplateCreateRequest(BaseModel):
    category: str = Field(min_length=1)
    spec_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_label: str = Field(min_length=1)
    value_type: Literal["string", "number", "boolean"]
    unit: Optional[str] = None


class ProductDetailChangeRequestCreate(BaseModel):
    proposed_specs: Optional[dict[str, Any]] = None
    proposed_description: Optional[str] = None
    proposed_official_url: Optional[str] = None
    proposed_image_url: Optional[str] = None


class ProductDetailChangeRequestReview(BaseModel):
    action: Literal["approve", "reject", "processing"]
    review_note: Optional[str] = None


class VideoProductMappingOverride(BaseModel):
    product_id: str = Field(min_length=1)
    role: Literal["primary", "secondary"] = "primary"


class ProductResolutionCandidateReview(BaseModel):
    product_id: str = Field(min_length=1)
    alias_text: Optional[str] = None
    sentiment_label: Optional[Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]] = None
