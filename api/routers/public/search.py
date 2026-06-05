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
    cache_key = f"search:v3:{q.lower().strip()}:{category}:{limit}"
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
        WITH latest_ranking AS (
            SELECT
                product_id,
                ROW_NUMBER() OVER (
                    ORDER BY bayesian_score DESC, statement_count DESC, total_mention_count DESC, product_id ASC
                ) AS rank,
                bayesian_score,
                controversy_label,
                total_mention_count,
                total_mentions,
                statement_count,
                question_count,
                positive_count,
                negative_count
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (
                SELECT MAX(ranking_date)
                FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            )
        )
        SELECT
            p.product_id,
            p.product_name,
            p.brand,
            p.category,
            COALESCE(r.rank, 0) AS rank,
            COALESCE(r.bayesian_score, 0.0) AS bayesian_score,
            r.controversy_label,
            COALESCE(r.total_mention_count, 0) AS total_mentions,
            COALESCE(r.total_mention_count, 0) AS total_mention_count,
            COALESCE(r.statement_count, 0) AS statement_count,
            COALESCE(r.question_count, 0) AS question_count,
            SAFE_DIVIDE(COALESCE(r.positive_count, 0) * 100.0, r.statement_count) AS positive_pct,
            SAFE_DIVIDE(COALESCE(r.negative_count, 0) * 100.0, r.statement_count) AS negative_pct
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
        LEFT JOIN latest_ranking r ON p.product_id = r.product_id
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
            total_mention_count=row["total_mention_count"],
            statement_count=row["statement_count"],
            question_count=row["question_count"],
            positive_pct=round(float(row["positive_pct"] or 0), 1),
            negative_pct=round(float(row["negative_pct"] or 0), 1),
        )
        for row in rows
    ]

    result = SearchResponse(results=items, total=len(items), query=q_clean)
    set_cached(cache_key, result.model_dump(mode="json"), _CACHE_TTL)
    return result
