from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


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


class AttentionItem(BaseModel):
    level: Literal["warning", "info"]
    message: str


class AdminDashboardResponse(BaseModel):
    pipeline_status: PipelineStatus
    quick_stats: QuickStat
    recent_dag_runs: list[DagRunSummary]
    attention_items: list[AttentionItem]
    as_of_date: date
