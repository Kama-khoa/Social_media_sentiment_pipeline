import hashlib
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery

from api.bq_client import query_to_list
from api.cache import invalidate_prefix
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.request_schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    KeywordCreateRequest,
    KeywordUpdateRequest,
)
from api.schemas.response_schemas import ChannelConfigItem, KeywordConfigItem

router = APIRouter(prefix="/admin", tags=["admin"])


def _bq_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[ChannelConfigItem])
def list_channels(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT channel_id, channel_name, channel_url, channel_handle,
               subscriber_count, is_active, is_historically_scanned,
               created_at, last_updated_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        ORDER BY is_active DESC, channel_name ASC
        """
    )
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
    existing = query_to_list(
        f"SELECT channel_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config` WHERE channel_id = @cid",
        [bigquery.ScalarQueryParameter("cid", "STRING", body.channel_id)],
    )
    if existing:
        raise HTTPException(status_code=409, detail="channel_id already exists")

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
            bigquery.ScalarQueryParameter("cid", "STRING", body.channel_id),
            bigquery.ScalarQueryParameter("name", "STRING", body.channel_name),
            bigquery.ScalarQueryParameter("url", "STRING", body.channel_url),
            bigquery.ScalarQueryParameter("handle", "STRING", body.channel_handle),
            bigquery.ScalarQueryParameter("subs", "INT64", body.subscriber_count),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return ChannelConfigItem(
        channel_id=body.channel_id,
        channel_name=body.channel_name,
        channel_url=body.channel_url,
        channel_handle=body.channel_handle,
        subscriber_count=body.subscriber_count,
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
    now = _bq_now()

    client = _get_bq_client()
    client.query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.channel_config`
        SET channel_name = @name, channel_url = @url, channel_handle = @handle,
            subscriber_count = @subs, last_updated_at = @now
        WHERE channel_id = @cid
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", channel_id),
            bigquery.ScalarQueryParameter("name", "STRING", new_name),
            bigquery.ScalarQueryParameter("url", "STRING", new_url),
            bigquery.ScalarQueryParameter("handle", "STRING", new_handle),
            bigquery.ScalarQueryParameter("subs", "INT64", new_subs),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return ChannelConfigItem(
        channel_id=channel_id,
        channel_name=new_name,
        channel_url=new_url,
        channel_handle=new_handle,
        subscriber_count=new_subs,
        is_active=row["is_active"],
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


# ── Keywords ──────────────────────────────────────────────────────────────────

@router.get("/keywords", response_model=list[KeywordConfigItem])
def list_keywords(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT keyword_id, keyword_text, search_cluster, is_active, created_at, last_updated_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config`
        ORDER BY is_active DESC, keyword_text ASC
        """
    )
    return [
        KeywordConfigItem(
            keyword_id=r["keyword_id"],
            keyword_text=r["keyword_text"],
            search_cluster=r.get("search_cluster"),
            is_active=r["is_active"],
            created_at=r["created_at"],
            last_updated_at=r.get("last_updated_at"),
        )
        for r in rows
    ]


@router.post("/keywords", response_model=KeywordConfigItem, status_code=201)
def create_keyword(body: KeywordCreateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    keyword_id = hashlib.md5(body.keyword_text.strip().lower().encode()).hexdigest()

    existing = query_to_list(
        f"SELECT keyword_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config` WHERE keyword_id = @kid",
        [bigquery.ScalarQueryParameter("kid", "STRING", keyword_id)],
    )
    if existing:
        raise HTTPException(status_code=409, detail="Keyword already exists")

    now = _bq_now()
    client = _get_bq_client()
    client.query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config`
        (keyword_id, keyword_text, search_cluster, is_active, created_at, last_updated_at)
        VALUES (@kid, @text, @cluster, TRUE, @now, @now)
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("kid", "STRING", keyword_id),
            bigquery.ScalarQueryParameter("text", "STRING", body.keyword_text.strip()),
            bigquery.ScalarQueryParameter("cluster", "STRING", body.search_cluster),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return KeywordConfigItem(
        keyword_id=keyword_id,
        keyword_text=body.keyword_text.strip(),
        search_cluster=body.search_cluster,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
    )


@router.put("/keywords/{keyword_id}", response_model=KeywordConfigItem)
def update_keyword(keyword_id: str, body: KeywordUpdateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    existing = query_to_list(
        f"""
        SELECT keyword_id, keyword_text, search_cluster, is_active, created_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config`
        WHERE keyword_id = @kid
        """,
        [bigquery.ScalarQueryParameter("kid", "STRING", keyword_id)],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")

    row = existing[0]
    new_text = body.keyword_text.strip() if body.keyword_text else row["keyword_text"]
    new_cluster = body.search_cluster if body.search_cluster is not None else row.get("search_cluster")
    now = _bq_now()

    client = _get_bq_client()
    client.query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config`
        SET keyword_text = @text, search_cluster = @cluster, last_updated_at = @now
        WHERE keyword_id = @kid
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("kid", "STRING", keyword_id),
            bigquery.ScalarQueryParameter("text", "STRING", new_text),
            bigquery.ScalarQueryParameter("cluster", "STRING", new_cluster),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()

    return KeywordConfigItem(
        keyword_id=keyword_id,
        keyword_text=new_text,
        search_cluster=new_cluster,
        is_active=row["is_active"],
        created_at=row["created_at"],
        last_updated_at=datetime.now(timezone.utc),
    )


@router.delete("/keywords/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    existing = query_to_list(
        f"SELECT keyword_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config` WHERE keyword_id = @kid",
        [bigquery.ScalarQueryParameter("kid", "STRING", keyword_id)],
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")

    now = _bq_now()
    client = _get_bq_client()
    client.query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config`
        SET is_active = FALSE, last_updated_at = @now
        WHERE keyword_id = @kid
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("kid", "STRING", keyword_id),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()
    invalidate_prefix("products:")
    invalidate_prefix("search:")


def _get_bq_client():
    from api.bq_client import get_bq_client
    return get_bq_client()
