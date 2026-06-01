import logging
from functools import lru_cache
from typing import Any

from google.cloud import bigquery

from api.config import get_settings

logger = logging.getLogger(__name__)

CONTROVERSY_MAP = {"cao": "high", "trung bình": "medium", "thấp": "low"}

CATEGORY_SLUG_MAP = {
    "all": None,
    "dien_thoai": "Điện thoại",
    "laptop": "Laptop",
    "tai_nghe": "Tai nghe",
    "smarthome": "Smarthome",
}


@lru_cache(maxsize=1)
def get_bq_client() -> bigquery.Client:
    settings = get_settings()
    return bigquery.Client(project=settings.gcp_project_id)


def query_to_list(sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict[str, Any]]:
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    try:
        rows = client.query(sql, job_config=job_config).result()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("BigQuery query failed: %s", exc)
        raise


def normalize_controversy(label: str | None) -> str:
    if label is None:
        return "low"
    return CONTROVERSY_MAP.get(label.strip(), label)
