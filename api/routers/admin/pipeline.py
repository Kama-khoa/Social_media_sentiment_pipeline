import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.bq_client import query_to_list
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.response_schemas import (
    AirflowHealth,
    DagRunDetail,
    DagRunsListResponse,
    PipelineHealthResponse,
    PipelineMetrics,
    TaskInstanceDetail,
    PipelineOpsSeries,
)

router = APIRouter(prefix="/admin/pipeline", tags=["pipeline"])

_AIRFLOW_TIMEOUT = 10.0
_DAG_IDS = ["youtube_daily_extraction_dag", "sentiment_analysis_dag", "analytics_dag", "seed_sync_dag"]
logger = logging.getLogger(__name__)


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


def _airflow_error_message(exc: HTTPException) -> str:
    if exc.status_code in (401, 403):
        return "Airflow authentication failed. Check AIRFLOW_API_USERNAME/AIRFLOW_API_PASSWORD."
    if exc.status_code == 404:
        return "Airflow endpoint or DAG was not found."
    if exc.status_code == 502:
        return "Cannot connect to Airflow webserver. Check AIRFLOW_BASE_URL and Docker networking."
    if exc.status_code == 504:
        return "Airflow request timed out."
    return str(exc.detail)


@router.get("/health", response_model=PipelineHealthResponse)
def pipeline_health(_: AppUser = Depends(require_admin)):
    settings = get_settings()

    health_data: dict | None = None
    dag_runs: list[DagRunDetail] = []
    airflow_message: str | None = None

    try:
        with _airflow_client(settings) as client:
            health_data = _safe_airflow_get(client, "/health")

            for dag_id in _DAG_IDS:
                try:
                    # Query single DAG info to get is_paused
                    dag_meta = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}")
                    is_paused = dag_meta.get("is_paused") if dag_meta else None

                    runs_data = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns?limit=1&order_by=-start_date")
                    
                    run = None
                    if runs_data and runs_data.get("dag_runs"):
                        run = runs_data["dag_runs"][0]

                    tasks: list[TaskInstanceDetail] = []
                    run_id = ""
                    state = "none"
                    start_date = None
                    duration_seconds = None

                    if run:
                        run_id = run.get("dag_run_id", "")
                        state = run.get("state", "unknown")
                        start_date = run.get("start_date") or run.get("execution_date")
                        end_date = run.get("end_date")
                        if start_date and end_date:
                            try:
                                from datetime import datetime as dt
                                start = dt.fromisoformat(start_date.replace("Z", "+00:00"))
                                end = dt.fromisoformat(end_date.replace("Z", "+00:00"))
                                duration_seconds = int((end - start).total_seconds())
                            except Exception:
                                pass

                        if run_id:
                            import urllib.parse
                            run_id_enc = urllib.parse.quote(run_id)
                            ti_data = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns/{run_id_enc}/taskInstances")
                            if ti_data:
                                for ti in ti_data.get("task_instances", []):
                                    tasks.append(TaskInstanceDetail(
                                        task_id=ti.get("task_id", ""),
                                        state=ti.get("state") or "none",
                                        duration=ti.get("duration"),
                                        try_number=ti.get("try_number", 1),
                                    ))

                    dag_runs.append(DagRunDetail(
                        dag_id=dag_id,
                        run_id=run_id,
                        state=state,
                        start_date=start_date,
                        duration_seconds=duration_seconds,
                        tasks=tasks,
                        is_paused=is_paused,
                    ))
                except HTTPException as exc:
                    if airflow_message is None:
                        airflow_message = _airflow_error_message(exc)
                    logger.warning("Could not fetch Airflow DAG %s: %s", dag_id, exc.detail)
                    dag_runs.append(DagRunDetail(
                        dag_id=dag_id,
                        run_id="",
                        state="none",
                        is_paused=None,
                        tasks=[]
                    ))
    except HTTPException as exc:
        airflow_message = _airflow_error_message(exc)

    airflow_health = AirflowHealth(
        webserver=health_data.get("metadatabase", {}).get("status", "unknown") if health_data else "unknown",
        scheduler=health_data.get("scheduler", {}).get("status", "unknown") if health_data else "unknown",
        message=airflow_message,
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


@router.get("/dags/{dag_id}/runs/{run_id}/tasks", response_model=list[TaskInstanceDetail])
def list_task_instances(dag_id: str, run_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    import urllib.parse
    run_id_enc = urllib.parse.quote(run_id)
    with _airflow_client(settings) as client:
        ti_data = _safe_airflow_get(client, f"/api/v1/dags/{dag_id}/dagRuns/{run_id_enc}/taskInstances")
        tasks = []
        if ti_data:
            for ti in ti_data.get("task_instances", []):
                tasks.append(TaskInstanceDetail(
                    task_id=ti.get("task_id", ""),
                    state=ti.get("state") or "none",
                    duration=ti.get("duration"),
                    try_number=ti.get("try_number", 1),
                ))
        return tasks


@router.get("/runs", response_model=DagRunsListResponse)
def list_all_dag_runs(
    dag_id: str | None = Query(None),
    state: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: AppUser = Depends(require_admin),
):
    settings = get_settings()
    path = f"/api/v1/dags/{dag_id}/dagRuns" if dag_id else "/api/v1/dags/~/dagRuns"
    
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "-start_date",
    }
    if state:
        params["state"] = state

    with _airflow_client(settings) as client:
        try:
            # Construct URL manually with parameters
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            resp_data = _safe_airflow_get(client, f"{path}?{param_str}")
        except HTTPException as e:
            if e.status_code == 404 and dag_id:
                # If DAG ID not found, return empty list instead of crashing
                return DagRunsListResponse(runs=[], total_count=0)
            raise e

        runs = []
        total_count = 0
        if resp_data:
            total_count = resp_data.get("total_entries", 0)
            for run in resp_data.get("dag_runs", []):
                run_dag_id = run.get("dag_id", "")
                run_id = run.get("dag_run_id", "")
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

                runs.append(DagRunDetail(
                    dag_id=run_dag_id,
                    run_id=run_id,
                    state=run.get("state", "unknown"),
                    start_date=start_date,
                    duration_seconds=duration_seconds,
                    tasks=[],  # Empty list; frontend pre-fetches tasks on-demand
                ))

        return DagRunsListResponse(runs=runs, total_count=total_count)


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


@router.get("/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs/{try_number}")
def get_task_log(dag_id: str, run_id: str, task_id: str, try_number: int, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        try:
            import urllib.parse
            run_id_enc = urllib.parse.quote(run_id)
            # Note: Airflow API returns plain text for logs if Accept is text/plain.
            # We fetch it and return as JSON wrapper.
            resp = client.get(f"/api/v1/dags/{dag_id}/dagRuns/{run_id_enc}/taskInstances/{task_id}/logs/{try_number}?full_content=true")
            resp.raise_for_status()
            return {"content": resp.text}
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
    quota_rows = []
    quota_queries = [
        f"""
        SELECT total_units_used, comments_collected, videos_discovered
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.quota_daily_summary`
        ORDER BY summary_date DESC
        LIMIT 1
        """,
        f"""
        SELECT total_units_used, comments_crawled AS comments_collected, videos_discovered
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.quota_daily_summary`
        ORDER BY quota_date DESC
        LIMIT 1
        """,
    ]
    for sql in quota_queries:
        try:
            quota_rows = query_to_list(sql)
            break
        except Exception as exc:
            logger.warning("Could not fetch quota metrics with fallback query: %s", exc)
    quota = quota_rows[0] if quota_rows else {}

    pending_rows = []
    try:
        pending_rows = query_to_list(
            f"""
            SELECT COUNT(*) AS cnt
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
            WHERE is_active = TRUE AND is_historically_scanned = FALSE
            """
        )
    except Exception as exc:
        logger.warning("Could not fetch pending channel metrics: %s", exc)
    pending = pending_rows[0]["cnt"] if pending_rows else 0

    nlp_rows = []
    nlp_queries = [
        f"""
        SELECT dag_run_id
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.raw_sentiment_results`
        ORDER BY processed_at DESC
        LIMIT 1
        """,
        f"""
        SELECT dag_run_id
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.raw_sentiment_results`
        ORDER BY processed_at DESC
        LIMIT 1
        """,
    ]
    for sql in nlp_queries:
        try:
            nlp_rows = query_to_list(sql)
            break
        except Exception as exc:
            logger.warning("Could not fetch NLP metrics with fallback query: %s", exc)
    last_nlp = nlp_rows[0]["dag_run_id"] if nlp_rows else None

    nlp_fallback_rate = None
    if last_nlp:
        try:
            rate_rows = query_to_list(
                f"""
                SELECT COUNTIF(inference_model = 'gemini-1.5-flash') / NULLIF(COUNT(*), 0) AS rate
                FROM `{settings.gcp_project_id}.{settings.bq_dataset}.raw_sentiment_results`
                WHERE dag_run_id = '{last_nlp}'
                """
            )
            if rate_rows and rate_rows[0]["rate"] is not None:
                nlp_fallback_rate = float(rate_rows[0]["rate"])
        except Exception as exc:
            logger.warning("Could not calculate NLP fallback rate: %s", exc)

    return PipelineMetrics(
        quota_used_today=int(quota.get("total_units_used") or 0),
        quota_limit=10000,
        videos_crawled_today=int(quota.get("videos_discovered") or 0),
        comments_crawled_today=int(quota.get("comments_collected") or 0),
        channels_pending_historical=int(pending),
        last_nlp_batch_id=last_nlp,
        nlp_fallback_rate=nlp_fallback_rate,
    )


@router.get("/series", response_model=PipelineOpsSeries)
def pipeline_series(_: AppUser = Depends(require_admin)):
    # Trả về dữ liệu chuỗi 15 ngày cho "Chỉ số vận hành".
    # Ở bản demo này, chúng ta sử dụng dữ liệu mô phỏng tương tự admin.jsx.
    return PipelineOpsSeries(
        ops_series=[11200, 14300, 9500, 18400, 22100, 15000, 13200, 19400, 25600, 17800, 21000, 24500, 28900, 20100, 26700],
        nlp_series=[85.4, 86.1, 86.8, 87.5, 88.2, 89.0, 91.5, 93.2, 94.8, 95.5, 96.2, 97.0, 97.4, 97.5, 97.7],
        videos_today=850,
        comments_today=15400,
        pipeline_latency="2.1s",
        nlp_accuracy="97.7%"
    )


class UpdateDagPayload(BaseModel):
    is_paused: bool


class UpdateTaskStatePayload(BaseModel):
    new_state: str


@router.patch("/dags/{dag_id}")
def update_dag(dag_id: str, payload: UpdateDagPayload, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    with _airflow_client(settings) as client:
        try:
            resp = client.patch(
                f"/api/v1/dags/{dag_id}?update_mask=is_paused",
                json={"is_paused": payload.is_paused}
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Cannot connect to Airflow webserver")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Airflow request timed out")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Airflow error: {exc.response.text[:200]}")


@router.post("/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/state")
def update_task_state(
    dag_id: str,
    run_id: str,
    task_id: str,
    payload: UpdateTaskStatePayload,
    _: AppUser = Depends(require_admin),
):
    settings = get_settings()
    with _airflow_client(settings) as client:
        try:
            resp = client.post(
                f"/api/v1/dags/{dag_id}/updateTaskInstancesState",
                json={
                    "dag_run_id": run_id,
                    "task_id": task_id,
                    "new_state": payload.new_state,
                    "dry_run": False
                }
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Cannot connect to Airflow webserver")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Airflow request timed out")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Airflow error: {exc.response.text[:200]}")
