from datetime import date

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, require_admin
from api.models import AppUser
from api.schemas.response_schemas import (
    AdminDashboardResponse,
    AttentionItem,
    CategoryStat,
    CausalEventSummary,
    DagRunSummary,
    PipelineStatus,
    QuickStat,
    TopProduct,
    UserDashboardResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TODAY = date(2026, 6, 1)

_MOCK_CATEGORY_STATS = [
    CategoryStat(category="dien_thoai", label="Điện thoại", mention_count=1204, week_change_pct=12.3),
    CategoryStat(category="laptop", label="Laptop", mention_count=432, week_change_pct=-3.1),
    CategoryStat(category="tai_nghe", label="Tai nghe", mention_count=281, week_change_pct=8.7),
    CategoryStat(category="smarthome", label="Smarthome", mention_count=95, week_change_pct=22.4),
]

_MOCK_TOP_PRODUCTS = [
    TopProduct(rank=1, product_id="samsung-galaxy-s25", product_name="Samsung Galaxy S25",
               brand="Samsung", category="Điện thoại", bayesian_score=0.72,
               controversy_label="low", total_mentions=1204, positive_pct=64.2,
               negative_pct=22.8, top_aspect="Pin"),
    TopProduct(rank=2, product_id="iphone-16-pro", product_name="iPhone 16 Pro",
               brand="Apple", category="Điện thoại", bayesian_score=0.68,
               controversy_label="high", total_mentions=987, positive_pct=58.1,
               negative_pct=31.4, top_aspect="Camera"),
    TopProduct(rank=3, product_id="xiaomi-15-ultra", product_name="Xiaomi 15 Ultra",
               brand="Xiaomi", category="Điện thoại", bayesian_score=0.61,
               controversy_label="medium", total_mentions=543, positive_pct=55.7,
               negative_pct=28.3, top_aspect="Hiệu năng"),
    TopProduct(rank=4, product_id="macbook-air-m3", product_name="MacBook Air M3",
               brand="Apple", category="Laptop", bayesian_score=0.74,
               controversy_label="low", total_mentions=412, positive_pct=71.3,
               negative_pct=14.2, top_aspect="Hiệu năng"),
    TopProduct(rank=5, product_id="oppo-reno-13", product_name="OPPO Reno 13",
               brand="OPPO", category="Điện thoại", bayesian_score=0.58,
               controversy_label="low", total_mentions=321, positive_pct=60.4,
               negative_pct=19.7, top_aspect="Thiết kế"),
]

_MOCK_CAUSAL_EVENTS = [
    CausalEventSummary(
        product_name="iPhone 16 Pro",
        change_point_date=date(2026, 5, 28),
        sentiment_direction="POSITIVE",
        event_video_title="Mở hộp iPhone 16 Pro chính hãng VN/A — Có đáng mua?",
        event_view_count=2_100_000,
        explanation_text="Biến động cảm xúc tích cực có thể tương quan với video review iPhone 16 Pro đạt 2.1 triệu lượt xem, trong đó nhiều bình luận ghi nhận cải thiện đáng kể ở khía cạnh Camera và Pin.",
    ),
    CausalEventSummary(
        product_name="Samsung Galaxy S25",
        change_point_date=date(2026, 5, 21),
        sentiment_direction="NEGATIVE",
        event_video_title="Galaxy S25 sau 1 tháng dùng thực tế — Sự thật không được PR",
        event_view_count=890_000,
        explanation_text="Xu hướng cảm xúc tiêu cực được ghi nhận có thể tương quan với video đánh giá dài hạn, trong đó người dùng phản ánh vấn đề về nhiệt độ máy.",
    ),
]

_MOCK_PIPELINE_STATUS = PipelineStatus(
    airflow_webserver="healthy",
    airflow_scheduler="healthy",
    quota_used_today=1800,
    quota_limit=10000,
    last_nlp_batch_run_id="scheduled__2026-06-01T20:00:00+00:00",
    nlp_fallback_pct=6.2,
)

_MOCK_QUICK_STATS = QuickStat(
    videos_today=34,
    comments_today=1204,
    products_tracked=47,
    active_channels=18,
    active_keywords=94,
)

_MOCK_DAG_RUNS = [
    DagRunSummary(dag_id="youtube_daily_extraction_dag", run_id="scheduled__2026-06-01T19:00:00+00:00",
                  state="success", start_date="2026-06-01T19:00:11Z", duration_seconds=252),
    DagRunSummary(dag_id="sentiment_analysis_dag", run_id="scheduled__2026-06-01T20:00:00+00:00",
                  state="success", start_date="2026-06-01T20:00:08Z", duration_seconds=513),
    DagRunSummary(dag_id="seed_sync_dag", run_id="manual__2026-05-30T08:15:00+00:00",
                  state="success", start_date="2026-05-30T08:15:02Z", duration_seconds=12),
]

_MOCK_ATTENTION_ITEMS = [
    AttentionItem(level="warning", message="keyword_config: 3 từ khóa đang bị vô hiệu hóa (is_active=FALSE)"),
    AttentionItem(level="info", message="channel_config: 1 kênh chưa hoàn thành historical scan"),
    AttentionItem(level="info", message="analytics_dag chưa được tạo — PELT attribution chưa tự động"),
]


@router.get("/user", response_model=UserDashboardResponse)
def user_dashboard(current_user: AppUser = Depends(get_current_user)):
    return UserDashboardResponse(
        category_stats=_MOCK_CATEGORY_STATS,
        top_products=_MOCK_TOP_PRODUCTS,
        latest_causal_events=_MOCK_CAUSAL_EVENTS,
        as_of_date=TODAY,
    )


@router.get("/admin", response_model=AdminDashboardResponse)
def admin_dashboard(current_user: AppUser = Depends(require_admin)):
    return AdminDashboardResponse(
        pipeline_status=_MOCK_PIPELINE_STATUS,
        quick_stats=_MOCK_QUICK_STATS,
        recent_dag_runs=_MOCK_DAG_RUNS,
        attention_items=_MOCK_ATTENTION_ITEMS,
        as_of_date=TODAY,
    )
