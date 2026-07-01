from datetime import date

from fastapi import APIRouter, HTTPException, Response
from google.cloud import bigquery

from api.bq_client import CATEGORY_SLUG_MAP, normalize_controversy, query_to_list
from api.cache import get_cached, set_cached
from api.config import get_settings
from api.routers.product_helpers import json_value
from api.schemas.response_schemas import (
    AspectSentiment,
    AttributionResponse,
    CategoryStat,
    CausalEventSummary,
    ProductDetailResponse,
    ProductDetails,
    ProductCommentItem,
    ProductSpecTemplateItem,
    TopProduct,
)

router = APIRouter(prefix="/products", tags=["products"])

_CACHE_TTL = 300


def _cache_key(path: str) -> str:
    return f"products:v2:{path}"


@router.get("/stats", response_model=list[CategoryStat])
def get_category_stats(response: Response):
    cache_key = _cache_key("stats")
    cached = get_cached(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    response.headers["X-Cache"] = "MISS"
    settings = get_settings()

    rows = query_to_list(f"""
        WITH current_date_cte AS (
            SELECT MAX(ranking_date) AS max_date FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
        ),
        current_stats AS (
            SELECT category, SUM(total_mention_count) AS mention_count
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (SELECT max_date FROM current_date_cte)
            GROUP BY category
        ),
        prev_stats AS (
            SELECT category, SUM(total_mention_count) AS mention_count
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (SELECT DATE_SUB(max_date, INTERVAL 7 DAY) FROM current_date_cte)
            GROUP BY category
        )
        SELECT 
            c.category, 
            c.mention_count,
            p.mention_count AS prev_mention_count
        FROM current_stats c
        LEFT JOIN prev_stats p ON c.category = p.category
    """)

    result = []
    total_curr = sum((r["mention_count"] or 0) for r in rows)
    total_prev = sum((r["prev_mention_count"] or 0) for r in rows)
    all_pct = 0.0
    if total_prev > 0:
        all_pct = round(((total_curr - total_prev) / total_prev) * 100, 1)
    elif total_curr > 0:
        all_pct = 100.0
        
    result.append(CategoryStat(category="all", label="Tất cả", mention_count=total_curr, week_change_pct=all_pct))

    for r in sorted(rows, key=lambda x: x["mention_count"] or 0, reverse=True):
        slug = next((k for k, v in CATEGORY_SLUG_MAP.items() if v == r["category"]), None)
        if slug is None:
            slug = r["category"].lower().replace(" ", "_")
            
        curr = r["mention_count"] or 0
        prev = r["prev_mention_count"] or 0
        pct = 0.0
        if prev > 0:
            pct = round(((curr - prev) / prev) * 100, 1)
        elif curr > 0:
            pct = 100.0
            
        result.append(
            CategoryStat(
                category=slug,
                label=r["category"],
                mention_count=curr,
                week_change_pct=pct,
            )
        )

    set_cached(cache_key, [item.model_dump(mode="json") for item in result], _CACHE_TTL)
    return result


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
        WITH filtered_products AS (
            SELECT
                r.product_id,
                p.product_name,
                p.brand,
                p.category,
                r.bayesian_score,
                r.controversy_label,
                r.total_mention_count,
                r.total_mentions,
                r.statement_count,
                r.question_count,
                SAFE_DIVIDE(r.positive_count * 100.0, r.statement_count) AS positive_pct,
                SAFE_DIVIDE(r.negative_count * 100.0, r.statement_count) AS negative_pct,
                r.top_aspect
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking` r
            JOIN `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
              ON r.product_id = p.product_id
            WHERE r.ranking_date = (
                SELECT MAX(ranking_date)
                FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            )
            {"AND p.category = @category" if category_label else ""}
        ),
        ranked_products AS (
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY CASE WHEN statement_count >= 5 THEN 1 ELSE 0 END DESC, bayesian_score DESC, statement_count DESC, total_mention_count DESC, product_id ASC
                ) AS rank,
                *
            FROM filtered_products
        )
        SELECT *
        FROM ranked_products
        ORDER BY rank ASC
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
            total_mentions=r["total_mention_count"],
            total_mention_count=r["total_mention_count"],
            statement_count=r["statement_count"],
            question_count=r["question_count"],
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
               d.specs, d.description, d.official_url, d.image_url, d.updated_at,
               r.bayesian_score, r.controversy_label, r.total_mention_count, r.total_mentions,
               r.statement_count, r.question_count
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
        LEFT JOIN `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` d
          ON p.product_id = d.product_id
        LEFT JOIN (
            SELECT product_id, bayesian_score, controversy_label, total_mention_count, total_mentions,
                   statement_count, question_count
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
          AND sentence_type = 'statement'
        GROUP BY aspect_label
        ORDER BY total_mentions DESC
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    template_rows = query_to_list(
        f"""
        SELECT category, spec_key, display_label, value_type, unit, is_active
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_spec_templates`
        WHERE category = @category AND is_active = TRUE
        ORDER BY display_label
        """,
        [bigquery.ScalarQueryParameter("category", "STRING", p["category"])],
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
        total_mention_count=p["total_mention_count"] or 0,
        statement_count=p["statement_count"] or 0,
        question_count=p["question_count"] or 0,
        aspects=aspects,
        details=ProductDetails(
            specs=json_value(p.get("specs")),
            description=p.get("description"),
            official_url=p.get("official_url"),
            image_url=p.get("image_url"),
            updated_at=p.get("updated_at"),
        ),
        spec_templates=[ProductSpecTemplateItem(**row) for row in template_rows],
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

    trend_rows = query_to_list(
        f"""
        SELECT
            mention_date,
            AVG(CASE
                WHEN UPPER(sentiment_label) = 'POSITIVE' THEN 1.0
                WHEN UPPER(sentiment_label) = 'NEGATIVE' THEN -1.0
                ELSE 0.0
            END) AS avg_sentiment
        FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.fact_product_mentions`
        WHERE product_id = @product_id
          AND aspect_label != 'NONE'
        GROUP BY mention_date
        ORDER BY mention_date ASC
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )

    from api.schemas.response_schemas import AttributionPoint
    trend = [
        AttributionPoint(
            date=str(row["mention_date"]),
            sentiment_score=float(row["avg_sentiment"])
        )
        for row in trend_rows
    ]

    result = AttributionResponse(
        product_id=product_id,
        product_name=product_rows[0]["product_name"],
        events=events,
        trend=trend,
    )
    set_cached(cache_key, result.model_dump(mode="json"), _CACHE_TTL)
    return result


@router.get("/{product_id}/comments", response_model=list[ProductCommentItem])
def get_product_comments(product_id: str, response: Response, limit: int = 30):
    cache_key = _cache_key(f"{product_id}/comments/{limit}")
    cached = get_cached(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    response.headers["X-Cache"] = "MISS"
    settings = get_settings()
    rows = query_to_list(
        f"""
        WITH deduplicated AS (
            SELECT
                f.comment_id,
                COALESCE(c.author_display_name, 'Người dùng YouTube') AS author,
                s.sentence_text AS text,
                f.aspect_label,
                UPPER(f.sentiment_label) AS sentiment_label,
                f.confidence_score,
                s.published_at
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.fact_product_mentions` f
            JOIN `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_comment_sentences` s
              ON f.sentence_id = s.sentence_id
            LEFT JOIN `{settings.gcp_project_id}.{settings.bq_dataset}_staging.stg_youtube_comments` c
              ON f.comment_id = c.comment_id
            WHERE f.product_id = @product_id
              AND f.aspect_label != 'NONE'
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY f.sentence_id, f.aspect_label
                ORDER BY f.confidence_score DESC
            ) = 1
        )
        SELECT *
        FROM deduplicated
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY sentiment_label
            ORDER BY published_at DESC, confidence_score DESC
        ) <= @limit
        ORDER BY sentiment_label, published_at DESC, confidence_score DESC
        """,
        [
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("limit", "INT64", min(max(limit, 1), 100)),
        ],
    )
    result = [
        ProductCommentItem(
            comment_id=row["comment_id"],
            author=row["author"],
            text=row["text"],
            aspect_label=row["aspect_label"],
            sentiment_label=row["sentiment_label"],
            confidence_score=round(float(row["confidence_score"] or 0), 4),
            published_at=row.get("published_at"),
        )
        for row in rows
    ]
    set_cached(cache_key, [item.model_dump(mode="json") for item in result], _CACHE_TTL)
    return result
