from fastapi import APIRouter, Response

from google.cloud import bigquery

from api.bq_client import normalize_controversy, query_to_list
from api.cache import get_cached, set_cached
from api.config import get_settings
from api.schemas.response_schemas import SearchResponse, SearchResultItem

router = APIRouter(prefix="/search", tags=["search"])

_CACHE_TTL = 300
_VALID_CATEGORIES = {"Điện thoại", "Laptop", "Tai nghe"}


@router.get("", response_model=SearchResponse)
def search_products(q: str = "", category: str = "", limit: int = 20, response: Response = None):
    cache_key = f"search:v2:{q.lower().strip()}:{category}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        if response:
            response.headers["X-Cache"] = "HIT"
        return cached

    if response:
        response.headers["X-Cache"] = "MISS"

    settings = get_settings()
    q_clean = q.strip()
    cat_clean = category.strip()

    filters = ["p.is_active = TRUE"]
    params: list[bigquery.ScalarQueryParameter] = []

    if q_clean:
        filters.append("LOWER(p.product_name) LIKE @q OR LOWER(p.brand) LIKE @q")
        params.append(bigquery.ScalarQueryParameter("q", "STRING", f"%{q_clean.lower()}%"))

    if cat_clean and cat_clean in _VALID_CATEGORIES:
        filters.append("p.category = @category")
        params.append(bigquery.ScalarQueryParameter("category", "STRING", cat_clean))

    where_clause = " AND ".join(filters)

    sql = f"""
        SELECT
            p.product_id,
            p.product_name,
            p.brand,
            p.category,
            COALESCE(r.rank_position, 0) AS rank,
            COALESCE(r.bayesian_score, 0.0) AS bayesian_score,
            r.controversy_label,
            COALESCE(r.total_mentions, 0) AS total_mentions,
            SAFE_DIVIDE(COALESCE(r.positive_count, 0) * 100.0, r.total_mentions) AS positive_pct,
            SAFE_DIVIDE(COALESCE(r.negative_count, 0) * 100.0, r.total_mentions) AS negative_pct
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
        LEFT JOIN (
            SELECT product_id, rank_position, bayesian_score, controversy_label,
                   total_mentions, positive_count, negative_count
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (
                SELECT MAX(ranking_date)
                FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            )
        ) r ON p.product_id = r.product_id
        WHERE {where_clause}
        ORDER BY total_mentions DESC
        LIMIT @limit
    """
    params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    rows = query_to_list(sql, params)
    items = [
        SearchResultItem(
            rank=row["rank"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            brand=row["brand"],
            category=row["category"],
            bayesian_score=round(float(row["bayesian_score"] or 0), 4),
            controversy_label=normalize_controversy(row.get("controversy_label")),
            total_mentions=row["total_mentions"],
            positive_pct=round(float(row["positive_pct"] or 0), 1),
            negative_pct=round(float(row["negative_pct"] or 0), 1),
        )
        for row in rows
    ]

    result = SearchResponse(results=items, total=len(items), query=q_clean)
    set_cached(cache_key, result.model_dump(mode="json"), _CACHE_TTL)
    return result
