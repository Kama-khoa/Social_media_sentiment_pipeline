from datetime import date

from fastapi import APIRouter, Depends

from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.routers.dashboard_helpers import (
    _build_attention_items,
    _fetch_airflow_health,
    _get_last_nlp_run,
    _get_mention_series,
    _get_quick_stats,
    _get_quota_today,
)
from api.schemas.response_schemas import AdminDashboardResponse, PipelineStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/admin", response_model=AdminDashboardResponse)
async def admin_dashboard(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    project = settings.gcp_project_id
    dataset = settings.bq_dataset
    marts = settings.bq_marts_dataset

    webserver_status, scheduler_status, dag_runs = await _fetch_airflow_health(settings)
    quota_used, quota_limit = _get_quota_today(project, dataset)
    last_nlp_run_id = _get_last_nlp_run(project, dataset)
    quick_stats = _get_quick_stats(project, dataset, marts)
    mention_series = _get_mention_series(project, marts)
    attention_items = _build_attention_items(project, dataset, marts)

    pipeline_status = PipelineStatus(
        airflow_webserver=webserver_status if webserver_status in ("healthy", "unhealthy") else "unknown",
        airflow_scheduler=scheduler_status if scheduler_status in ("healthy", "unhealthy") else "unknown",
        quota_used_today=quota_used,
        quota_limit=quota_limit,
        last_nlp_batch_run_id=last_nlp_run_id,
        nlp_fallback_pct=None,
    )

    return AdminDashboardResponse(
        pipeline_status=pipeline_status,
        quick_stats=quick_stats,
        mention_series=mention_series,
        recent_dag_runs=dag_runs,
        attention_items=attention_items,
        as_of_date=date.today(),
    )
