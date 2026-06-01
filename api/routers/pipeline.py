from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException

from api.bq_client import query_to_list
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.response_schemas import (
    AirflowHealth,
    DagRunDetail,
    PipelineHealthResponse,
    PipelineMetrics,
    TaskInstanceDetail,
)

router = APIRouter(prefix="/admin/pipeline", tags=["pipeline"])

_AIRFLOW_TIMEOUT = 10.0
_DAG_IDS = ["youtube_daily_extraction_dag", "sentiment_analysis_dag", "seed_sync_dag"]


def _airflow_client(settings) -> httpx.Client:
    return httpx.Client(
        base_url=settings.airflow_base_url,
        auth=(settings.airflow_api_username, settings.airflow_api_password),
        timeout=_AIRFLOW_TIMEOUT,
    )


def _safe_airflow_get(client: httpx.Client, path: str) -> dict | None:
    try:
        resp = client.get(path)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot connect to Airflow webserver")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Airflow request timed out")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Airflow error: {exc.response.text[:200]}")


@router.get("/health", response_model=PipelineHealthResponse)
def pipeline_health(_: AppUser = Depends(require_admin)):
    settings = get_settings()

    with _airflow_client(settings) as client:
        health_data = _safe_airflow_get(client, "/health")

        dag_runs: list[DagRunDetail] = []
        for dag_id in _DAG_IDS:
            runs_data = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns?limit=1&order_by=-start_date")
            if not runs_data or not runs_data.get("dag_runs"):
                continue

            run = runs_data["dag_runs"][0]
            run_id = run.get("run_id", "")

            tasks: list[TaskInstanceDetail] = []
            if run_id:
                ti_data = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances")
                if ti_data:
                    for ti in ti_data.get("task_instances", []):
                        tasks.append(TaskInstanceDetail(
                            task_id=ti.get("task_id", ""),
                            state=ti.get("state") or "none",
                            duration=ti.get("duration"),
                            try_number=ti.get("try_number", 1),
                        ))

            start_date = run.get("start_date") or run.get("execution_date")
            end_date = run.get("end_date")
            duration_seconds = None
            if start_date and end_date:
                try:
                    from datetime import datetime as dt
                    start = dt.fromisoformat(start_date.replace("Z", "+00:00"))
                    end = dt.fromisoformat(end_date.replace("Z", "+00:00"))
                    duration_seconds = int((end - start).total_seconds())
                except Exception:
                    pass

            dag_runs.append(DagRunDetail(
                dag_id=dag_id,
                run_id=run_id,
                state=run.get("state", "unknown"),
                start_date=start_date,
                duration_seconds=duration_seconds,
                tasks=tasks,
            ))

    airflow_health = AirflowHealth(
        webserver=health_data.get("metadatabase", {}).get("status", "unknown") if health_data else "unknown",
        scheduler=health_data.get("scheduler", {}).get("status", "unknown") if health_data else "unknown",
    )

    metrics = _fetch_bq_metrics(settings)

    return PipelineHealthResponse(
        airflow=airflow_health,
        recent_dag_runs=dag_runs,
        metrics=metrics,
        as_of=datetime.now(timezone.utc),
    )


@router.get("/dags")
def list_dags(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        return _safe_airflow_get(client, "/api/v1/dags")


@router.get("/dags/{dag_id}/runs")
def list_dag_runs(dag_id: str, limit: int = 10, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        return _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns?limit={limit}&order_by=-start_date")


@router.get("/dags/{dag_id}/runs/{run_id}/tasks")
def list_task_instances(dag_id: str, run_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        return _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances")


@router.post("/dags/{dag_id}/trigger")
def trigger_dag(dag_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        try:
            resp = client.post(f"/api/v1/dags/{dag_id}/dagRuns", json={})
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Cannot connect to Airflow webserver")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Airflow request timed out")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Airflow error: {exc.response.text[:200]}")


@router.get("/metrics", response_model=PipelineMetrics)
def pipeline_metrics(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    return _fetch_bq_metrics(settings)


def _fetch_bq_metrics(settings) -> PipelineMetrics:
    quota_rows = query_to_list(
        f"""
        SELECT total_units_used, comments_collected, videos_discovered
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.quota_daily_summary`
        WHERE summary_date = CURRENT_DATE()
        LIMIT 1
        """
    )
    quota = quota_rows[0] if quota_rows else {}

    pending_rows = query_to_list(
        f"""
        SELECT COUNT(*) AS cnt
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        WHERE is_active = TRUE AND is_historically_scanned = FALSE
        """
    )
    pending = pending_rows[0]["cnt"] if pending_rows else 0

    nlp_rows = query_to_list(
        f"""
        SELECT dag_run_id
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.raw_sentiment_results`
        ORDER BY processed_at DESC
        LIMIT 1
        """
    )
    last_nlp = nlp_rows[0]["dag_run_id"] if nlp_rows else None

    return PipelineMetrics(
        quota_used_today=int(quota.get("total_units_used") or 0),
        quota_limit=10000,
        videos_crawled_today=int(quota.get("videos_discovered") or 0),
        comments_crawled_today=int(quota.get("comments_collected") or 0),
        channels_pending_historical=int(pending),
        last_nlp_batch_id=last_nlp,
    )
