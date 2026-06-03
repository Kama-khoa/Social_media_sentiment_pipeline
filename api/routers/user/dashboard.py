from datetime import date

from fastapi import APIRouter, Depends

from api.config import get_settings
from api.dependencies import get_current_user
from api.models import AppUser
from api.routers.dashboard_helpers import _get_category_stats, _get_causal_events, _get_top_products
from api.schemas.response_schemas import UserDashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/user", response_model=UserDashboardResponse)
def user_dashboard(_: AppUser = Depends(get_current_user)):
    settings = get_settings()
    project = settings.gcp_project_id
    marts = settings.bq_marts_dataset

    try:
        top_products = _get_top_products(project, marts, limit=5)
    except Exception:
        top_products = []

    try:
        category_stats = _get_category_stats(project, marts)
    except Exception:
        category_stats = []

    causal_events = _get_causal_events(project, marts, limit=3)

    return UserDashboardResponse(
        category_stats=category_stats,
        top_products=top_products,
        latest_causal_events=causal_events,
        as_of_date=date.today(),
    )
