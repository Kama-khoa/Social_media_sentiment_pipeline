import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from google.cloud import bigquery

from api.bq_client import CATEGORY_SLUG_MAP, get_bq_client, normalize_controversy, query_to_list
from api.cache import get_cached, set_cached
from api.config import get_settings
from api.schemas.response_schemas import (
    AspectSentiment,
    AttributionResponse,
    CausalEventSummary,
    ProductDetailResponse,
    TopProduct,
)

router = APIRouter(prefix="/products", tags=["products"])

_CACHE_TTL = 300


def _cache_key(path: str) -> str:
    return f"products:{path}"


@router.get("/top/{category}", response_model=list[TopProduct])
def get_top_products(category: str, response: Response, limit: int = 20):
    cache_key = _cache_key(f"top/{category}/{limit}")
    cached = get_cached(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    response.headers["X-Cache"] = "MISS"
    settings = get_settings()
    category_label = CATEGORY_SLUG_MAP.get(category)

    sql = f"""
        SELECT
            r.rank_position AS rank,
            r.product_id,
            p.product_name,
            p.brand,
            p.category,
            r.bayesian_score,
            r.controversy_label,
            r.total_mentions,
            SAFE_DIVIDE(r.positive_count * 100.0, r.total_mentions) AS positive_pct,
            SAFE_DIVIDE(r.negative_count * 100.0, r.total_mentions) AS negative_pct,
            r.top_aspect
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking` r
        JOIN `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
          ON r.product_id = p.product_id
        WHERE r.ranking_date = (
            SELECT MAX(ranking_date)
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
        )
        {"AND p.category = @category" if category_label else ""}
        ORDER BY r.rank_position ASC
        LIMIT @limit
    """

    params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    if category_label:
        params.append(bigquery.ScalarQueryParameter("category", "STRING", category_label))

    rows = query_to_list(sql, params)
    result = [
        TopProduct(
            rank=r["rank"],
            product_id=r["product_id"],
            product_name=r["product_name"],
            brand=r["brand"],
            category=r["category"],
            bayesian_score=round(float(r["bayesian_score"] or 0), 4),
            controversy_label=normalize_controversy(r.get("controversy_label")),
            total_mentions=r["total_mentions"],
            positive_pct=round(float(r["positive_pct"] or 0), 1),
            negative_pct=round(float(r["negative_pct"] or 0), 1),
            top_aspect=r.get("top_aspect"),
        )
        for r in rows
    ]
    set_cached(cache_key, [item.model_dump(mode="json") for item in result], _CACHE_TTL)
    return result


@router.get("/{product_id}/aspects", response_model=ProductDetailResponse)
def get_product_aspects(product_id: str, response: Response):
    cache_key = _cache_key(f"{product_id}/aspects")
    cached = get_cached(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    response.headers["X-Cache"] = "MISS"
    settings = get_settings()

    product_rows = query_to_list(
        f"""
        SELECT p.product_id, p.product_name, p.brand, p.category,
               r.bayesian_score, r.controversy_label, r.total_mentions
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
        LEFT JOIN (
            SELECT product_id, bayesian_score, controversy_label, total_mentions
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (
                SELECT MAX(ranking_date)
                FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            )
        ) r ON p.product_id = r.product_id
        WHERE p.product_id = @product_id AND p.is_active = TRUE
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )

    if not product_rows:
        raise HTTPException(status_code=404, detail="Product not found")

    p = product_rows[0]

    aspect_rows = query_to_list(
        f"""
        SELECT
            aspect_label,
            COUNTIF(UPPER(sentiment_label) = 'POSITIVE') AS positive_count,
            COUNTIF(UPPER(sentiment_label) = 'NEGATIVE') AS negative_count,
            COUNTIF(UPPER(sentiment_label) = 'NEUTRAL') AS neutral_count,
            COUNT(*) AS total_mentions
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.fact_product_mentions`
        WHERE product_id = @product_id
          AND aspect_label != 'NONE'
        GROUP BY aspect_label
        ORDER BY total_mentions DESC
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )

    aspects = [
        AspectSentiment(
            aspect_label=a["aspect_label"],
            positive_count=a["positive_count"],
            negative_count=a["negative_count"],
            neutral_count=a["neutral_count"],
            total_mentions=a["total_mentions"],
            positive_pct=round(a["positive_count"] * 100.0 / a["total_mentions"], 1) if a["total_mentions"] else 0.0,
            negative_pct=round(a["negative_count"] * 100.0 / a["total_mentions"], 1) if a["total_mentions"] else 0.0,
        )
        for a in aspect_rows
    ]

    result = ProductDetailResponse(
        product_id=p["product_id"],
        product_name=p["product_name"],
        brand=p["brand"],
        category=p["category"],
        bayesian_score=round(float(p["bayesian_score"] or 0), 4),
        controversy_label=normalize_controversy(p.get("controversy_label")),
        total_mentions=p["total_mentions"] or 0,
        aspects=aspects,
        as_of_date=date.today(),
    )
    set_cached(cache_key, result.model_dump(mode="json"), _CACHE_TTL)
    return result


@router.get("/{product_id}/attribution", response_model=AttributionResponse)
def get_product_attribution(product_id: str, response: Response):
    cache_key = _cache_key(f"{product_id}/attribution")
    cached = get_cached(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    response.headers["X-Cache"] = "MISS"
    settings = get_settings()

    product_rows = query_to_list(
        f"""
        SELECT product_name FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products`
        WHERE product_id = @product_id AND is_active = TRUE
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not product_rows:
        raise HTTPException(status_code=404, detail="Product not found")

    event_rows = query_to_list(
        f"""
        SELECT
            product_id,
            change_point_date,
            event_video_title,
            event_view_count,
            sentiment_direction,
            explanation_text
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.causal_events`
        WHERE product_id = @product_id
        ORDER BY change_point_date DESC
        LIMIT 10
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )

    events = [
        CausalEventSummary(
            product_name=product_rows[0]["product_name"],
            change_point_date=e["change_point_date"],
            sentiment_direction=e["sentiment_direction"],
            event_video_title=e.get("event_video_title") or "",
            event_view_count=e.get("event_view_count") or 0,
            explanation_text=e.get("explanation_text") or "",
        )
        for e in event_rows
    ]

    result = AttributionResponse(
        product_id=product_id,
        product_name=product_rows[0]["product_name"],
        events=events,
    )
    set_cached(cache_key, result.model_dump(mode="json"), _CACHE_TTL)
    return result
