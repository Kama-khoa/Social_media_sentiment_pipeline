import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import requests
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery

from api.bq_client import query_to_list
from api.cache import invalidate_prefix
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.request_schemas import (
    ChannelCrawlRequest,
    ChannelCreateRequest,
    ChannelUpdateRequest,
    KeywordCreateRequest,
    KeywordUpdateRequest,
)
from api.schemas.response_schemas import ChannelConfigItem, KeywordConfigItem

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

_YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
_SEARCH_UNITS_PER_CALL = 100
_CHANNEL_SEED_UNITS_PER_CALL = 1
_YOUTUBE_DAG_ID = "youtube_daily_extraction_dag"


def _bq_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _normalize_channel_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Vui lòng nhập URL kênh YouTube.")
    if value.startswith("@"):
        return f"https://www.youtube.com/{value}"
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if not any(domain in host for domain in ("youtube.com", "www.youtube.com", "m.youtube.com")):
        raise HTTPException(status_code=422, detail="URL phải là kênh YouTube hợp lệ.")
    return value.rstrip("/")


def _parse_channel_url(raw: str) -> tuple[str | None, str | None, str]:
    url = _normalize_channel_url(raw)
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = [part for part in path.split("/") if part]

    channel_id = None
    handle = None
    if len(parts) >= 2 and parts[0] == "channel" and parts[1].startswith("UC"):
        channel_id = parts[1]
    else:
        match = re.search(r"@[\w.-]+", path)
        if match:
            handle = match.group(0)

    if channel_id is None and handle is None:
        raise HTTPException(
            status_code=422,
            detail="Chỉ hỗ trợ URL dạng https://www.youtube.com/@handle hoặc /channel/UC...",
        )
    return channel_id, handle, url


def _fetch_quota_used_by_bucket(settings) -> dict[str, int]:
    rows = query_to_list(
        f"""
        SELECT bucket, SUM(units_used) AS total
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.quota_operation_log`
        WHERE DATE(created_at) = CURRENT_DATE()
        GROUP BY bucket
        """
    )
    return {str(row["bucket"]): int(row.get("total") or 0) for row in rows}


def _quota_remaining(settings, bucket: str, allocation: int) -> int:
    try:
        used = _fetch_quota_used_by_bucket(settings).get(bucket, 0)
        return max(0, allocation - used)
    except Exception as exc:
        logger.warning("Could not read quota usage for bucket %s: %s", bucket, exc)
        return allocation


def _log_quota_operation(settings, operation_type: str, bucket: str, units: int, dag_run_id: str) -> None:
    client = _get_bq_client()
    now = datetime.now(timezone.utc)
    client.insert_rows_json(
        f"{settings.gcp_project_id}.{settings.bq_dataset}.quota_operation_log",
        [{
            "log_id": hashlib.md5(f"{operation_type}:{dag_run_id}:{now.isoformat()}".encode()).hexdigest(),
            "log_date": now.date().isoformat(),
            "dag_run_id": dag_run_id,
            "operation_type": operation_type,
            "bucket": bucket,
            "units_used": units,
            "videos_processed": 0,
            "comments_collected": 0,
            "execution_time_seconds": None,
            "created_at": now.isoformat(),
        }],
    )


def _resolve_channel_metadata(channel_url: str, settings) -> dict:
    channel_id, handle, normalized_url = _parse_channel_url(channel_url)
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Thiếu YOUTUBE_API_KEY để resolve kênh YouTube.")

    remaining = _quota_remaining(settings, "channel_seed", 500)
    if remaining < _CHANNEL_SEED_UNITS_PER_CALL:
        raise HTTPException(
            status_code=429,
            detail="Đã hết quota channel_seed hôm nay, chưa thể thêm kênh mới bằng YouTube API.",
        )

    params = {"part": "snippet,statistics", "key": api_key}
    if channel_id:
        params["id"] = channel_id
    elif handle:
        params["forHandle"] = handle

    try:
        response = requests.get(_YOUTUBE_CHANNELS_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Could not resolve channel URL %s: %s", normalized_url, exc)
        raise HTTPException(status_code=502, detail="Không thể gọi YouTube API để resolve kênh.")

    data = response.json()
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh YouTube từ URL này.")

    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    resolved_handle = handle or snippet.get("customUrl")
    if resolved_handle and not resolved_handle.startswith("@"):
        resolved_handle = f"@{resolved_handle}"

    _log_quota_operation(settings, "channel_seed", "channel_seed", _CHANNEL_SEED_UNITS_PER_CALL, "admin_channel_create")
    return {
        "channel_id": item["id"],
        "channel_name": snippet.get("title") or item["id"],
        "channel_url": normalized_url,
        "channel_handle": resolved_handle,
        "subscriber_count": int(statistics["subscriberCount"]) if statistics.get("subscriberCount") else None,
    }


def _airflow_trigger(settings, dag_id: str, conf: dict) -> dict:
    try:
        with httpx.Client(
            base_url=settings.airflow_base_url,
            auth=(settings.airflow_api_username, settings.airflow_api_password),
            timeout=10.0,
        ) as client:
            resp = client.post(f"/api/v1/dags/{dag_id}/dagRuns", json={"conf": conf})
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot connect to Airflow webserver")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Airflow request timed out")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Airflow error: {exc.response.text[:200]}")


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels/quota")
def get_channel_quota(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    search_remaining = _quota_remaining(settings, "search_videos", 9000)
    return {"search_remaining": search_remaining}


@router.get("/channels", response_model=list[ChannelConfigItem])
def list_channels(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    try:
        rows = query_to_list(
            f"""
            SELECT channel_id, channel_name, channel_url, channel_handle,
                   subscriber_count, is_active, is_historically_scanned,
                   created_at, last_updated_at
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
            ORDER BY is_active DESC, channel_name ASC
            """
        )
    except Exception as exc:
        logger.warning("Could not list channels: %s", exc)
        raise HTTPException(status_code=502, detail="Không thể tải channel_config từ BigQuery.")
    return [
        ChannelConfigItem(
            channel_id=r["channel_id"],
            channel_name=r["channel_name"],
            channel_url=r.get("channel_url"),
            channel_handle=r.get("channel_handle"),
            subscriber_count=r.get("subscriber_count"),
            is_active=r["is_active"],
            is_historically_scanned=r["is_historically_scanned"],
            created_at=r["created_at"],
            last_updated_at=r.get("last_updated_at"),
        )
        for r in rows
    ]


@router.post("/channels", response_model=ChannelConfigItem, status_code=201)
def create_channel(body: ChannelCreateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    resolved = _resolve_channel_metadata(body.channel_url, settings)
    existing = query_to_list(
        f"SELECT channel_id, channel_name, is_active FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config` WHERE channel_id = @cid",
        [bigquery.ScalarQueryParameter("cid", "STRING", resolved["channel_id"])],
    )
    if existing:
        row = existing[0]
        status = "đang hoạt động" if row["is_active"] else "đã bị tắt"
        raise HTTPException(
            status_code=409, 
            detail=f"Kênh này đã tồn tại trong hệ thống với tên '{row['channel_name']}' (trạng thái: {status})."
        )

    now = _bq_now()
    client = _get_bq_client()
    client.query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        (channel_id, channel_name, channel_url, channel_handle, subscriber_count,
         is_active, is_historically_scanned, created_at, last_updated_at)
        VALUES (@cid, @name, @url, @handle, @subs, TRUE, FALSE, @now, @now)
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", resolved["channel_id"]),
            bigquery.ScalarQueryParameter("name", "STRING", resolved["channel_name"]),
            bigquery.ScalarQueryParameter("url", "STRING", resolved["channel_url"]),
            bigquery.ScalarQueryParameter("handle", "STRING", resolved["channel_handle"]),
            bigquery.ScalarQueryParameter("subs", "INT64", resolved["subscriber_count"]),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return ChannelConfigItem(
        channel_id=resolved["channel_id"],
        channel_name=resolved["channel_name"],
        channel_url=resolved["channel_url"],
        channel_handle=resolved["channel_handle"],
        subscriber_count=resolved["subscriber_count"],
        is_active=True,
        is_historically_scanned=False,
        created_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
    )


@router.put("/channels/{channel_id}", response_model=ChannelConfigItem)
def update_channel(channel_id: str, body: ChannelUpdateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    existing = query_to_list(
        f"""
        SELECT channel_id, channel_name, channel_url, channel_handle, subscriber_count,
               is_active, is_historically_scanned, created_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        WHERE channel_id = @cid
        """,
        [bigquery.ScalarQueryParameter("cid", "STRING", channel_id)],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Channel not found")

    row = existing[0]
    new_name = body.channel_name or row["channel_name"]
    new_url = body.channel_url if body.channel_url is not None else row.get("channel_url")
    new_handle = body.channel_handle if body.channel_handle is not None else row.get("channel_handle")
    new_subs = body.subscriber_count if body.subscriber_count is not None else row.get("subscriber_count")
    new_active = body.is_active if body.is_active is not None else row["is_active"]
    now = _bq_now()

    client = _get_bq_client()
    client.query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        SET channel_name = @name, channel_url = @url, channel_handle = @handle,
            subscriber_count = @subs, is_active = @active, last_updated_at = @now
        WHERE channel_id = @cid
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", channel_id),
            bigquery.ScalarQueryParameter("name", "STRING", new_name),
            bigquery.ScalarQueryParameter("url", "STRING", new_url),
            bigquery.ScalarQueryParameter("handle", "STRING", new_handle),
            bigquery.ScalarQueryParameter("subs", "INT64", new_subs),
            bigquery.ScalarQueryParameter("active", "BOOL", new_active),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return ChannelConfigItem(
        channel_id=channel_id,
        channel_name=new_name,
        channel_url=new_url,
        channel_handle=new_handle,
        subscriber_count=new_subs,
        is_active=new_active,
        is_historically_scanned=row["is_historically_scanned"],
        created_at=row["created_at"],
        last_updated_at=datetime.now(timezone.utc),
    )


@router.delete("/channels/{channel_id}", status_code=204)
def delete_channel(channel_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    existing = query_to_list(
        f"SELECT channel_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config` WHERE channel_id = @cid",
        [bigquery.ScalarQueryParameter("cid", "STRING", channel_id)],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Channel not found")

    now = _bq_now()
    client = _get_bq_client()
    client.query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        SET is_active = FALSE, last_updated_at = @now
        WHERE channel_id = @cid
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", channel_id),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()


@router.post("/channels/{channel_id}/crawl")
def crawl_channel(channel_id: str, body: ChannelCrawlRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    existing = query_to_list(
        f"""
        SELECT channel_id, is_active
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        WHERE channel_id = @cid
        """,
        [bigquery.ScalarQueryParameter("cid", "STRING", channel_id)],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not existing[0]["is_active"]:
        raise HTTPException(status_code=400, detail="Kênh đang tắt, không thể crawl.")

    search_remaining = _quota_remaining(settings, "search_videos", 9000)
    if body.preferred_mode == "ytdlp":
        crawl_mode = "ytdlp"
    elif body.preferred_mode == "api":
        crawl_mode = "api_or_ytdlp"
    else:
        crawl_mode = "api_or_ytdlp" if search_remaining >= _SEARCH_UNITS_PER_CALL else "ytdlp"

    conf = {
        "manual_channel_crawl": True,
        "channel_id": channel_id,
        "lookback_days": body.lookback_days,
        "crawl_mode": crawl_mode,
    }
    result = _airflow_trigger(settings, _YOUTUBE_DAG_ID, conf)
    return {
        "dag_id": _YOUTUBE_DAG_ID,
        "run_id": result.get("dag_run_id") or result.get("run_id"),
        "crawl_mode": crawl_mode,
        "quota_remaining": search_remaining,
        "lookback_days": body.lookback_days,
    }


def _get_bq_client():
    from api.bq_client import get_bq_client
    return get_bq_client()
