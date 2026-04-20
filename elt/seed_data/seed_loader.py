from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from google.cloud import bigquery

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
_DATASET = os.environ["BQ_DATASET"]
_YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
_GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

_YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

_CSV_DIR = Path(__file__).parent
_SEED_CHANNELS_CSV = _CSV_DIR / "seed_channels.csv"
_SEED_KEYWORDS_CSV = _CSV_DIR / "seed_keywords.csv"


def _get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=_PROJECT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_handle(raw: str) -> str:
    raw = raw.strip()
    match = re.search(r"@[\w.-]+", raw)
    if match:
        return match.group(0)
    raise ValueError(f"Cannot parse YouTube handle from: '{raw}'")


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _fetch_channels_from_api(handles: list[str]) -> list[dict]:
    results = []
    batch_size = 50
    for i in range(0, len(handles), batch_size):
        batch = handles[i : i + batch_size]
        records = _fetch_channel_batch(batch)
        results.extend(records)
        if i + batch_size < len(handles):
            time.sleep(0.5)
    return results


def _fetch_channel_batch(handles: list[str]) -> list[dict]:
    records = []
    for handle in handles:
        params = {
            "part": "snippet,statistics",
            "forHandle": handle,
            "key": _YOUTUBE_API_KEY,
        }
        response = requests.get(_YOUTUBE_CHANNELS_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            print(f"  WARNING: No channel found for handle {handle}, skipping.")
            continue

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        records.append({
            "channel_id": item["id"],
            "channel_name": snippet.get("title", ""),
            "channel_handle": handle,
            "subscriber_count": int(statistics.get("subscriberCount", 0)),
        })
        time.sleep(0.2)

    return records


def _merge_channels_to_bq(client: bigquery.Client, records: list[dict]) -> int:
    if not records:
        return 0

    now = _now_iso()
    rows = [
        {
            "channel_id": r["channel_id"],
            "channel_name": r["channel_name"],
            "channel_url": f"https://www.youtube.com/{r['channel_handle']}",
            "channel_handle": r["channel_handle"],
            "subscriber_count": r["subscriber_count"],
            "is_active": True,
            "is_historically_scanned": False,
            "historical_scan_completed_at": None,
            "created_at": now,
            "last_updated_at": now,
        }
        for r in records
    ]

    tmp_table = f"{_PROJECT_ID}.{_DATASET}._tmp_seed_channels_{uuid.uuid4().hex[:8]}"
    schema = [
        bigquery.SchemaField("channel_id", "STRING"),
        bigquery.SchemaField("channel_name", "STRING"),
        bigquery.SchemaField("channel_url", "STRING"),
        bigquery.SchemaField("channel_handle", "STRING"),
        bigquery.SchemaField("subscriber_count", "INT64"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("is_historically_scanned", "BOOL"),
        bigquery.SchemaField("historical_scan_completed_at", "TIMESTAMP"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("last_updated_at", "TIMESTAMP"),
    ]
    tmp = bigquery.Table(tmp_table, schema=schema)
    client.create_table(tmp, exists_ok=True)
    client.insert_rows_json(tmp_table, rows)
    time.sleep(2)

    merge_sql = f"""
        MERGE `{_PROJECT_ID}.{_DATASET}.channel_config` AS target
        USING `{tmp_table}` AS source
        ON target.channel_id = source.channel_id
        WHEN MATCHED THEN UPDATE SET
            target.channel_name        = source.channel_name,
            target.subscriber_count    = source.subscriber_count,
            target.last_updated_at     = source.last_updated_at
        WHEN NOT MATCHED THEN INSERT (
            channel_id, channel_name, channel_url, channel_handle,
            subscriber_count, is_active, is_historically_scanned,
            historical_scan_completed_at, created_at, last_updated_at
        ) VALUES (
            source.channel_id, source.channel_name, source.channel_url,
            source.channel_handle, source.subscriber_count, source.is_active,
            source.is_historically_scanned, source.historical_scan_completed_at,
            source.created_at, source.last_updated_at
        )
    """
    client.query(merge_sql).result()
    client.delete_table(tmp_table, not_found_ok=True)
    return len(rows)


def _merge_keywords_to_bq(client: bigquery.Client, rows: list[dict]) -> int:
    if not rows:
        return 0

    tmp_table = f"{_PROJECT_ID}.{_DATASET}._tmp_seed_keywords_{uuid.uuid4().hex[:8]}"
    schema = [
        bigquery.SchemaField("keyword_id", "STRING"),
        bigquery.SchemaField("keyword_text", "STRING"),
        bigquery.SchemaField("search_cluster", "STRING"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
    ]
    tmp = bigquery.Table(tmp_table, schema=schema)
    client.create_table(tmp, exists_ok=True)
    client.insert_rows_json(tmp_table, rows)
    time.sleep(2)

    merge_sql = f"""
        MERGE `{_PROJECT_ID}.{_DATASET}.keyword_config` AS target
        USING `{tmp_table}` AS source
        ON target.keyword_id = source.keyword_id
        WHEN MATCHED THEN UPDATE SET
            target.search_cluster = source.search_cluster,
            target.is_active      = source.is_active
        WHEN NOT MATCHED THEN INSERT (
            keyword_id, keyword_text, search_cluster, is_active, created_at
        ) VALUES (
            source.keyword_id, source.keyword_text, source.search_cluster,
            source.is_active, source.created_at
        )
    """
    client.query(merge_sql).result()
    client.delete_table(tmp_table, not_found_ok=True)
    return len(rows)


def seed_channels(client: bigquery.Client) -> int:
    df = pd.read_csv(_SEED_CHANNELS_CSV, dtype=str)
    df.columns = df.columns.str.strip()

    if "channel_handle" not in df.columns:
        raise ValueError("seed_channels.csv must have column: channel_handle")

    raw_handles = df["channel_handle"].dropna().str.strip().tolist()
    handles = [_parse_handle(h) for h in raw_handles]

    print(f"  Resolving {len(handles)} channel handles via YouTube API...")
    api_records = _fetch_channels_from_api(handles)
    print(f"  Resolved {len(api_records)}/{len(handles)} channels.")

    merged = _merge_channels_to_bq(client, api_records)
    return merged


def seed_keywords(client: bigquery.Client) -> int:
    df = pd.read_csv(_SEED_KEYWORDS_CSV, dtype=str)
    df.columns = df.columns.str.strip()

    if "keyword_text" not in df.columns:
        raise ValueError("seed_keywords.csv must have column: keyword_text")
    
    if "keyword_id" not in df.columns:
        raise ValueError("seed_keywords.csv must have column: keyword_id")

    df = df[["keyword_id", "keyword_text", "search_cluster"]].dropna(subset=["keyword_text"])
    df = df[df["keyword_text"].str.strip() != ""]
    df = df[df["keyword_id"].str.strip() != ""]
 
    now = _now_iso()
    rows = [
        {
            "keyword_id": row["keyword_id"].strip(),
            "keyword_text": row["keyword_text"].strip(),
            "search_cluster": row["search_cluster"].strip() if pd.notna(row["search_cluster"]) else None,
            "is_active": True,
            "created_at": now,
        }
        for _, row in df.iterrows()
    ]
 
    merged = _merge_keywords_to_bq(client, rows)
    return merged


def run() -> None:
    client = _get_bq_client()

    # print("=== Seeding channels ===")
    # channel_count = seed_channels(client)
    # print(f"  Done: {channel_count} channels upserted.\n")

    print("=== Seeding keywords ===")
    keyword_count = seed_keywords(client)
    print(f"  Done: {keyword_count} keywords upserted.\n")

    # print(f"Seed complete: {channel_count} channels, {keyword_count} keywords.")


if __name__ == "__main__":
    run()
