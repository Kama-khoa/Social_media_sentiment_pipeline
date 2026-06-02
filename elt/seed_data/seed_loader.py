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
_SEED_PRODUCTS_CSV = _CSV_DIR / "seed_products.csv"


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
    text = text.replace("+", " plus ")
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
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_json(rows, tmp_table, job_config=job_config)
    load_job.result()

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
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_json(rows, tmp_table, job_config=job_config)
    load_job.result()

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


def _merge_products_to_bq(client: bigquery.Client, product_rows: list[dict], alias_rows: list[dict]) -> int:
    if not product_rows:
        return 0

    product_tmp = f"{_PROJECT_ID}.{_DATASET}._tmp_seed_products_{uuid.uuid4().hex[:8]}"
    product_schema = [
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("brand", "STRING"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("release_year", "INT64"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
    ]
    client.load_table_from_json(
        product_rows, product_tmp,
        job_config=bigquery.LoadJobConfig(schema=product_schema, write_disposition="WRITE_TRUNCATE"),
    ).result()
    client.query(f"""
        MERGE `{_PROJECT_ID}.{_DATASET}.product_config` AS target
        USING `{product_tmp}` AS source
        ON target.product_id = source.product_id
        WHEN MATCHED THEN UPDATE SET
            target.product_name = source.product_name,
            target.brand = source.brand,
            target.category = source.category,
            target.updated_at = source.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
    """).result()
    client.delete_table(product_tmp, not_found_ok=True)

    alias_tmp = f"{_PROJECT_ID}.{_DATASET}._tmp_seed_product_aliases_{uuid.uuid4().hex[:8]}"
    alias_schema = [
        bigquery.SchemaField("alias_id", "STRING"),
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("alias_text", "STRING"),
        bigquery.SchemaField("alias_type", "STRING"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
    ]
    client.load_table_from_json(
        alias_rows, alias_tmp,
        job_config=bigquery.LoadJobConfig(schema=alias_schema, write_disposition="WRITE_TRUNCATE"),
    ).result()
    client.query(f"""
        MERGE `{_PROJECT_ID}.{_DATASET}.product_aliases` AS target
        USING `{alias_tmp}` AS source
        ON target.alias_id = source.alias_id
        WHEN MATCHED THEN UPDATE SET target.is_active = source.is_active
        WHEN NOT MATCHED THEN INSERT ROW
    """).result()
    client.delete_table(alias_tmp, not_found_ok=True)
    return len(product_rows)


def sync_products(client: bigquery.Client) -> dict:
    df = pd.read_csv(_SEED_PRODUCTS_CSV, dtype=str)
    df.columns = df.columns.str.strip()
    required_columns = {"product_name", "brand", "category"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"seed_products.csv missing columns: {', '.join(sorted(missing))}")
    for optional_column in ("product_id", "release_year", "aliases"):
        if optional_column not in df.columns:
            df[optional_column] = None
    df = df.dropna(subset=["product_name"])
    df = df[df["product_name"].str.strip() != ""]
    resolved_ids = df.apply(
        lambda row: (
            row["product_id"].strip()
            if pd.notna(row["product_id"]) and row["product_id"].strip()
            else _slugify(row["product_name"])
        ),
        axis=1,
    )
    duplicate_ids = sorted(set(resolved_ids[resolved_ids.duplicated()].tolist()))
    if duplicate_ids:
        raise ValueError(f"seed_products.csv duplicate product_id values: {', '.join(duplicate_ids)}")

    now = _now_iso()
    products = []
    aliases: dict[tuple[str, str], tuple[str, str, str]] = {}
    for _, row in df.iterrows():
        product_name = row["product_name"].strip()
        product_id = resolved_ids.loc[row.name]
        release_year = (
            int(row["release_year"])
            if pd.notna(row["release_year"]) and row["release_year"].strip()
            else None
        )
        products.append({
            "product_id": product_id,
            "product_name": product_name,
            "brand": row["brand"].strip() if pd.notna(row["brand"]) else None,
            "category": row["category"].strip() if pd.notna(row["category"]) else None,
            "release_year": release_year,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        aliases[(product_id, product_name.casefold())] = (product_id, product_name, "official")
        if pd.notna(row["aliases"]):
            for alias in row["aliases"].split("|"):
                if alias.strip():
                    normalized_alias = alias.strip()
                    aliases.setdefault(
                        (product_id, normalized_alias.casefold()),
                        (product_id, normalized_alias, "common_name"),
                    )
    alias_rows = [
        {
            "alias_id": _slugify(f"{product_id}-{alias_text}"),
            "product_id": product_id,
            "alias_text": alias_text,
            "alias_type": alias_type,
            "is_active": True,
            "created_at": now,
        }
        for product_id, alias_text, alias_type in sorted(aliases.values())
    ]
    synced = _merge_products_to_bq(client, products, alias_rows)
    return {"products": synced, "aliases": len(alias_rows)}


def sync_product_spec_templates(client: bigquery.Client) -> int:
    common: list[tuple[str, str, str, str | None]] = []
    templates = {
        "Điện thoại": [
            ("screen_size_inches", "Kích thước màn hình", "number", "inch"),
            ("screen_technology", "Công nghệ màn hình", "string", None),
            ("ram_gb", "RAM", "number", "GB"),
            ("storage_gb", "Bộ nhớ", "number", "GB"),
            ("battery_mah", "Dung lượng pin", "number", "mAh"),
            ("chipset", "Chipset", "string", None),
        ],
        "Laptop": [
            ("screen_size_inches", "Kích thước màn hình", "number", "inch"),
            ("ram_gb", "RAM", "number", "GB"),
            ("storage_gb", "Bộ nhớ", "number", "GB"),
            ("processor", "Bộ xử lý", "string", None),
            ("graphics", "Đồ họa", "string", None),
        ],
        "Tai nghe": [
            ("battery_hours", "Thời lượng pin", "number", "giờ"),
            ("connection", "Kết nối", "string", None),
            ("noise_cancellation", "Chống ồn chủ động", "boolean", None),
        ],
    }
    now = _now_iso()
    rows = [
        {
            "category": category,
            "spec_key": spec_key,
            "display_label": label,
            "value_type": value_type,
            "unit": unit,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        for category, items in templates.items()
        for spec_key, label, value_type, unit in common + items
    ]
    tmp_table = f"{_PROJECT_ID}.{_DATASET}._tmp_seed_product_templates_{uuid.uuid4().hex[:8]}"
    schema = [
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("spec_key", "STRING"),
        bigquery.SchemaField("display_label", "STRING"),
        bigquery.SchemaField("value_type", "STRING"),
        bigquery.SchemaField("unit", "STRING"),
        bigquery.SchemaField("is_active", "BOOL"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
    ]
    client.load_table_from_json(
        rows, tmp_table,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
    ).result()
    client.query(f"""
        MERGE `{_PROJECT_ID}.{_DATASET}.product_spec_templates` AS target
        USING `{tmp_table}` AS source
        ON target.category = source.category AND target.spec_key = source.spec_key
        WHEN MATCHED THEN UPDATE SET
            target.display_label = source.display_label,
            target.value_type = source.value_type,
            target.unit = source.unit,
            target.updated_at = source.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
    """).result()
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


def _get_existing_handles(client: bigquery.Client) -> set[str]:
    query = f"""
        SELECT channel_handle
        FROM `{_PROJECT_ID}.{_DATASET}.channel_config`
        WHERE is_active = TRUE
    """
    rows = client.query(query).result()
    return {row.channel_handle for row in rows}


def sync_channels(client: bigquery.Client) -> dict:
    df = pd.read_csv(_SEED_CHANNELS_CSV, dtype=str)
    df.columns = df.columns.str.strip()

    if "channel_handle" not in df.columns:
        return {"csv_total": 0, "new": 0, "synced": 0}

    raw_handles = df["channel_handle"].dropna().str.strip().tolist()
    csv_handles = [_parse_handle(h) for h in raw_handles]

    existing_handles = _get_existing_handles(client)
    new_handles = [h for h in csv_handles if h not in existing_handles]

    if not new_handles:
        return {"csv_total": len(csv_handles), "new": 0, "synced": 0}

    api_records = _fetch_channels_from_api(new_handles)
    synced = _merge_channels_to_bq(client, api_records)

    return {"csv_total": len(csv_handles), "new": len(new_handles), "synced": synced}


def sync_keywords(client: bigquery.Client) -> dict:
    df = pd.read_csv(_SEED_KEYWORDS_CSV, dtype=str)
    df.columns = df.columns.str.strip()

    if "keyword_text" not in df.columns or "keyword_id" not in df.columns:
        return {"csv_total": 0, "synced": 0}

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

    synced = _merge_keywords_to_bq(client, rows)
    return {"csv_total": len(rows), "synced": synced}


def run() -> None:
    client = _get_bq_client()

    print("=== Seeding channels ===")
    channel_count = seed_channels(client)
    print(f"  Done: {channel_count} channels upserted.\n")

    print("=== Seeding keywords ===")
    keyword_count = seed_keywords(client)
    print(f"  Done: {keyword_count} keywords upserted.\n")

    print("=== Seeding canonical products ===")
    product_result = sync_products(client)
    print(f"  Done: {product_result['products']} products, {product_result['aliases']} aliases upserted.\n")
    template_count = sync_product_spec_templates(client)
    print(f"  Done: {template_count} product specification templates upserted.\n")

    print(f"Seed complete: {channel_count} channels, {keyword_count} keywords, {product_result['products']} products.")


if __name__ == "__main__":
    run()
