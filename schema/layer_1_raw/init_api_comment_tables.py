import os

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _table_id(name: str) -> str:
    return f"{PROJECT_ID}.{DATASET}.{name}"


def create_raw_comments_api(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("parent_comment_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("author_channel_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("author_display_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("text_original", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("text_display", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("like_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("reply_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("is_reply", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("crawl_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("crawled_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("gcs_partition_date", "STRING", mode="REQUIRED"),
    ]
    table = bigquery.Table(_table_id("raw_comments_api"), schema=schema)
    table.description = (
        "Native raw comments table populated by YouTube Data API backfill. "
        "Rows are upserted by comment_id and preferred over GCS downloader rows."
    )
    client.create_table(table, exists_ok=True)
    print("raw_comments_api: OK")


def create_api_comment_backfill_state(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("comments_collected", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("pages_crawled", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("quota_units_used", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("last_page_token", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("last_error", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("last_crawled_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = bigquery.Table(_table_id("api_comment_backfill_state"), schema=schema)
    table.description = "Checkpoint table for YouTube API comment backfill."
    client.create_table(table, exists_ok=True)
    _ensure_columns(client, "api_comment_backfill_state", schema)
    print("api_comment_backfill_state: OK")


def _ensure_columns(client: bigquery.Client, table_name: str, required_schema: list[bigquery.SchemaField]) -> None:
    table = client.get_table(_table_id(table_name))
    existing = {field.name for field in table.schema}
    missing = [field for field in required_schema if field.name not in existing]
    if not missing:
        return

    table.schema = [*table.schema, *missing]
    client.update_table(table, ["schema"])


def run() -> None:
    client = get_client()
    create_raw_comments_api(client)
    create_api_comment_backfill_state(client)
    print("\nLayer 1 API comment tables created.")


if __name__ == "__main__":
    run()
