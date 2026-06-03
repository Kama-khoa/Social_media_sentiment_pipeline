import logging
from datetime import datetime, timezone

import httpx
from api.bq_client import normalize_controversy, query_to_list
from api.schemas.response_schemas import (
    AttentionItem,
    CategoryStat,
    CausalEventSummary,
    DailyMentionStat,
    DagRunSummary,
    QuickStat,
    TopProduct,
)

logger = logging.getLogger(__name__)

_CATEGORY_SLUG = {
    "Điện thoại": "dien_thoai",
    "Laptop": "laptop",
    "Tai nghe": "tai_nghe",
}

_DAG_IDS = ["youtube_daily_extraction_dag", "sentiment_analysis_dag", "analytics_dag"]
_VALID_RUN_STATES = {"success", "failed", "running", "queued"}


def _get_top_products(project: str, marts: str, limit: int = 5) -> list[TopProduct]:
    rows = query_to_list(f"""
        SELECT r.rank_position AS rank, r.product_id, p.product_name, p.brand, p.category,
               r.bayesian_score, r.controversy_label, r.total_mentions,
               SAFE_DIVIDE(r.positive_count * 100.0, r.total_mentions) AS positive_pct,
               SAFE_DIVIDE(r.negative_count * 100.0, r.total_mentions) AS negative_pct,
               r.top_aspect
        FROM `{project}.{marts}.agg_daily_product_ranking` r
        JOIN `{project}.{marts}.dim_products` p ON r.product_id = p.product_id
        WHERE r.ranking_date = (
            SELECT MAX(ranking_date) FROM `{project}.{marts}.agg_daily_product_ranking`
        )
        ORDER BY r.rank_position ASC
        LIMIT {limit}
    """)
    return [
        TopProduct(
            rank=r["rank"],
            product_id=r["product_id"],
            product_name=r["product_name"],
            brand=r["brand"],
            category=r["category"],
            bayesian_score=round(float(r["bayesian_score"] or 0), 4),
            controversy_label=normalize_controversy(r.get("controversy_label")),
            total_mentions=r["total_mentions"] or 0,
            positive_pct=round(float(r["positive_pct"] or 0), 1),
            negative_pct=round(float(r["negative_pct"] or 0), 1),
            top_aspect=r.get("top_aspect"),
        )
        for r in rows
    ]


def _get_category_stats(project: str, marts: str) -> list[CategoryStat]:
    rows = query_to_list(f"""
        SELECT category, SUM(total_mentions) AS mention_count
        FROM `{project}.{marts}.agg_daily_product_ranking`
        WHERE ranking_date = (
            SELECT MAX(ranking_date) FROM `{project}.{marts}.agg_daily_product_ranking`
        )
        GROUP BY category
        ORDER BY mention_count DESC
    """)
    return [
        CategoryStat(
            category=_CATEGORY_SLUG.get(r["category"], r["category"].lower().replace(" ", "_")),
            label=r["category"],
            mention_count=r["mention_count"] or 0,
            week_change_pct=0.0,
        )
        for r in rows
    ]


def _get_causal_events(project: str, marts: str, limit: int = 3) -> list[CausalEventSummary]:
    try:
        rows = query_to_list(f"""
            SELECT ce.product_id, p.product_name, ce.change_point_date,
                   ce.sentiment_direction, ce.event_video_title,
                   ce.event_view_count, ce.explanation_text
            FROM `{project}.{marts}.causal_events` ce
            JOIN `{project}.{marts}.dim_products` p ON ce.product_id = p.product_id
            ORDER BY ce.change_point_date DESC
            LIMIT {limit}
        """)
        return [
            CausalEventSummary(
                product_name=r["product_name"],
                change_point_date=r["change_point_date"],
                sentiment_direction=r["sentiment_direction"],
                event_video_title=r.get("event_video_title") or "",
                event_view_count=r.get("event_view_count") or 0,
                explanation_text=r.get("explanation_text") or "",
            )
            for r in rows
        ]
    except Exception:
        logger.warning("causal_events table not available or empty")
        return []


async def _fetch_airflow_health(settings) -> tuple[str, str, list[DagRunSummary]]:
    try:
        auth = (settings.airflow_api_username, settings.airflow_api_password)
        async with httpx.AsyncClient(timeout=5.0) as client:
            health = (await client.get(f"{settings.airflow_base_url}/health")).json()
            webserver = health.get("metadatabase", {}).get("status", "unknown")
            scheduler = health.get("scheduler", {}).get("status", "unknown")

            runs: list[DagRunSummary] = []
            for dag_id in _DAG_IDS:
                try:
                    resp = await client.get(
                        f"{settings.airflow_base_url}/api/v1/dags/{dag_id}/dagRuns",
                        auth=auth,
                        params={"limit": 1, "order_by": "-start_date"},
                    )
                    dag_runs = resp.json().get("dag_runs", [])
                    if dag_runs:
                        r = dag_runs[0]
                        end = r.get("end_date")
                        start = r.get("start_date")
                        duration = None
                        if start and end:
                            try:
                                duration = int(
                                    (datetime.fromisoformat(end.replace("Z", "+00:00"))
                                     - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()
                                )
                            except Exception:
                                pass
                        runs.append(DagRunSummary(
                            dag_id=dag_id,
                            run_id=r["run_id"],
                            state=r["state"] if r["state"] in _VALID_RUN_STATES else "failed",
                            start_date=r.get("start_date"),
                            duration_seconds=duration,
                        ))
                except Exception:
                    pass

            return webserver, scheduler, runs
    except Exception:
        return "unknown", "unknown", []


def _get_quick_stats(project: str, dataset: str, marts: str) -> QuickStat:
    try:
        rows = query_to_list(f"""
            SELECT
                (SELECT COUNT(*) FROM `{project}.{marts}.dim_products` WHERE is_active = TRUE) AS products_tracked,
                (SELECT COUNT(*) FROM `{project}.{dataset}.channel_config` WHERE is_active = TRUE) AS active_channels,
                (SELECT COUNT(*) FROM `{project}.{dataset}.keyword_config` WHERE is_active = TRUE) AS active_keywords,
                (SELECT COALESCE(SUM(videos_discovered), 0)
                 FROM `{project}.{dataset}.quota_daily_summary`
                 WHERE summary_date = CURRENT_DATE()) AS videos_today,
                (SELECT COALESCE(SUM(comments_collected), 0)
                 FROM `{project}.{dataset}.quota_daily_summary`
                 WHERE summary_date = CURRENT_DATE()) AS comments_today
        """)
        r = rows[0] if rows else {}
        return QuickStat(
            videos_today=int(r.get("videos_today") or 0),
            comments_today=int(r.get("comments_today") or 0),
            products_tracked=int(r.get("products_tracked") or 0),
            active_channels=int(r.get("active_channels") or 0),
            active_keywords=int(r.get("active_keywords") or 0),
        )
    except Exception:
        logger.warning("Could not fetch quick stats from BQ")
        return QuickStat(videos_today=0, comments_today=0, products_tracked=0, active_channels=0, active_keywords=0)


def _get_quota_today(project: str, dataset: str) -> tuple[int, int]:
    try:
        rows = query_to_list(f"""
            SELECT total_units_used
            FROM `{project}.{dataset}.quota_daily_summary`
            WHERE summary_date = CURRENT_DATE()
            LIMIT 1
        """)
        if rows:
            return int(rows[0].get("total_units_used") or 0), 10000
    except Exception:
        pass
    return 0, 10000


def _get_mention_series(project: str, marts: str) -> list[DailyMentionStat]:
    try:
        rows = query_to_list(f"""
            SELECT mention_date, COUNT(*) AS mention_count
            FROM `{project}.{marts}.fact_product_mentions`
            WHERE mention_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
            GROUP BY mention_date
            ORDER BY mention_date
        """)
        return [
            DailyMentionStat(
                mention_date=row["mention_date"],
                mention_count=int(row["mention_count"] or 0),
            )
            for row in rows
        ]
    except Exception:
        logger.warning("Could not fetch mention series from BQ")
        return []


def _get_last_nlp_run(project: str, dataset: str) -> str | None:
    try:
        rows = query_to_list(f"""
            SELECT dag_run_id
            FROM `{project}.{dataset}.raw_sentiment_results`
            ORDER BY created_at DESC
            LIMIT 1
        """)
        return rows[0]["dag_run_id"] if rows else None
    except Exception:
        return None


def _build_attention_items(project: str, dataset: str, marts: str) -> list[AttentionItem]:
    items: list[AttentionItem] = []
    try:
        pending = query_to_list(f"""
            SELECT COUNT(*) AS cnt
            FROM `{project}.{dataset}.channel_config`
            WHERE is_active = TRUE AND is_historically_scanned = FALSE
        """)
        if pending and (cnt := int(pending[0].get("cnt") or 0)) > 0:
            items.append(AttentionItem(
                level="info",
                message=f"channel_config: {cnt} kênh chưa hoàn thành historical scan",
            ))
    except Exception:
        pass

    try:
        inactive_kw = query_to_list(f"""
            SELECT COUNT(*) AS cnt
            FROM `{project}.{dataset}.keyword_config`
            WHERE is_active = FALSE
        """)
        if inactive_kw and (cnt := int(inactive_kw[0].get("cnt") or 0)) > 0:
            items.append(AttentionItem(
                level="warning",
                message=f"keyword_config: {cnt} từ khóa đang bị vô hiệu hóa (is_active=FALSE)",
            ))
    except Exception:
        pass

    try:
        causal_check = query_to_list(f"""
            SELECT MAX(change_point_date) AS last_run
            FROM `{project}.{marts}.causal_events`
        """)
        if not causal_check or not causal_check[0].get("last_run"):
            items.append(AttentionItem(
                level="info",
                message="analytics_dag chưa tạo causal_events — PELT attribution chưa có dữ liệu",
            ))
    except Exception:
        items.append(AttentionItem(
            level="info",
            message="causal_events chưa tồn tại — analytics_dag cần được chạy ít nhất 1 lần",
        ))

    return items
