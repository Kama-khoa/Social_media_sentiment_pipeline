from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ── Products / Analytics ──────────────────────────────────────────────────────

class AspectSentiment(BaseModel):
    aspect_label: str
    positive_count: int
    negative_count: int
    neutral_count: int
    total_mentions: int
    positive_pct: float
    negative_pct: float


class ProductDetailResponse(BaseModel):
    product_id: str
    product_name: str
    brand: str
    category: str
    bayesian_score: float
    controversy_label: str
    total_mentions: int
    aspects: list[AspectSentiment]
    details: Optional["ProductDetails"] = None
    spec_templates: list["ProductSpecTemplateItem"] = Field(default_factory=list)
    as_of_date: date


class ProductDetails(BaseModel):
    specs: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    official_url: Optional[str] = None
    image_url: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProductConfigItem(BaseModel):
    product_id: str
    product_name: str
    brand: Optional[str]
    category: Optional[str]
    release_year: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductAliasItem(BaseModel):
    alias_id: str
    product_id: str
    alias_text: str
    alias_type: str
    is_active: bool
    created_at: datetime


class ProductSpecTemplateItem(BaseModel):
    category: str
    spec_key: str
    display_label: str
    value_type: Literal["string", "number", "boolean"]
    unit: Optional[str]
    is_active: bool


class ProductDetailChangeRequestItem(BaseModel):
    request_id: str
    product_id: str
    proposed_specs: Optional[dict[str, Any]]
    proposed_description: Optional[str]
    proposed_official_url: Optional[str]
    proposed_image_url: Optional[str]
    submitted_by: str
    status: Literal["pending", "approved", "rejected"]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: datetime


class AttributionResponse(BaseModel):
    product_id: str
    product_name: str
    events: list["CausalEventSummary"]


class ProductCommentItem(BaseModel):
    comment_id: str
    author: str
    text: str
    aspect_label: str
    sentiment_label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    confidence_score: float
    published_at: Optional[datetime]


class SearchResultItem(BaseModel):
    rank: int
    product_id: str
    product_name: str
    brand: str
    category: str
    bayesian_score: float
    controversy_label: str
    total_mentions: int
    positive_pct: float
    negative_pct: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str


# ── Admin Config ──────────────────────────────────────────────────────────────

class ChannelConfigItem(BaseModel):
    channel_id: str
    channel_name: str
    channel_url: Optional[str]
    channel_handle: Optional[str]
    subscriber_count: Optional[int]
    is_active: bool
    is_historically_scanned: bool
    created_at: datetime
    last_updated_at: Optional[datetime]


class KeywordConfigItem(BaseModel):
    keyword_id: str
    keyword_text: str
    search_cluster: Optional[str]
    is_active: bool
    created_at: datetime
    last_updated_at: Optional[datetime]


# ── Pipeline Health ───────────────────────────────────────────────────────────

class AirflowHealth(BaseModel):
    webserver: str
    scheduler: str


class TaskInstanceDetail(BaseModel):
    task_id: str
    state: str
    duration: Optional[float]
    try_number: int


class DagRunDetail(BaseModel):
    dag_id: str
    run_id: str
    state: str
    start_date: Optional[str]
    duration_seconds: Optional[int]
    tasks: list[TaskInstanceDetail] = []


class PipelineMetrics(BaseModel):
    quota_used_today: int
    quota_limit: int
    videos_crawled_today: int
    comments_crawled_today: int
    channels_pending_historical: int
    last_nlp_batch_id: Optional[str]


class PipelineHealthResponse(BaseModel):
    airflow: AirflowHealth
    recent_dag_runs: list[DagRunDetail]
    metrics: PipelineMetrics
    as_of: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["user", "admin"]


class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime


class CategoryStat(BaseModel):
    category: str
    label: str
    mention_count: int
    week_change_pct: float


class TopProduct(BaseModel):
    rank: int
    product_id: str
    product_name: str
    brand: str
    category: str
    bayesian_score: float
    controversy_label: Literal["high", "medium", "low"]
    total_mentions: int
    positive_pct: float
    negative_pct: float
    top_aspect: Optional[str]


class CausalEventSummary(BaseModel):
    product_name: str
    change_point_date: date
    sentiment_direction: Literal["POSITIVE", "NEGATIVE"]
    event_video_title: str
    event_view_count: int
    explanation_text: str


class UserDashboardResponse(BaseModel):
    category_stats: list[CategoryStat]
    top_products: list[TopProduct]
    latest_causal_events: list[CausalEventSummary]
    as_of_date: date


class DagRunSummary(BaseModel):
    dag_id: str
    run_id: str
    state: Literal["success", "failed", "running", "queued"]
    start_date: Optional[str]
    duration_seconds: Optional[int]


class PipelineStatus(BaseModel):
    airflow_webserver: Literal["healthy", "unhealthy", "unknown"]
    airflow_scheduler: Literal["healthy", "unhealthy", "unknown"]
    quota_used_today: int
    quota_limit: int
    last_nlp_batch_run_id: Optional[str]
    nlp_fallback_pct: Optional[float]


class QuickStat(BaseModel):
    videos_today: int
    comments_today: int
    products_tracked: int
    active_channels: int
    active_keywords: int


class DailyMentionStat(BaseModel):
    mention_date: date
    mention_count: int


class AttentionItem(BaseModel):
    level: Literal["warning", "info"]
    message: str


class AdminDashboardResponse(BaseModel):
    pipeline_status: PipelineStatus
    quick_stats: QuickStat
    mention_series: list[DailyMentionStat]
    recent_dag_runs: list[DagRunSummary]
    attention_items: list[AttentionItem]
    as_of_date: date
