import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]

def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def table_ref(client: bigquery.Client, table_name: str) -> bigquery.Table:
    return bigquery.Table(f"{PROJECT_ID}.{DATASET}.{table_name}")


def create_channel_config(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_url", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("channel_handle", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("subscriber_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("is_active", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("is_historically_scanned", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("historical_scan_completed_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("last_updated_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "channel_config")
    table.schema = schema
    table.description = "T01 — Danh muc kenh YouTube can theo doi."
    client.create_table(table, exists_ok=True)
    print("channel_config: OK")


def create_keyword_config(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("keyword_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("keyword_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("search_cluster", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("is_active", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "keyword_config")
    table.schema = schema
    table.description = "T02 — Danh muc 100 keywords nhom theo semantic cluster."
    client.create_table(table, exists_ok=True)
    print("keyword_config: OK")


def create_video_crawl_state(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("keyword_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("search_mode", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("maturity_stage", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("comment_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("last_comment_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("total_comments_crawled", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("last_comment_crawled_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("is_comment_complete", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("last_page_token", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("crawl_status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "video_crawl_state")
    table.schema = schema
    table.description = "T03 — Trang thai vong doi tung video: new, growing, mature, archived."
    client.create_table(table, exists_ok=True)
    print("video_crawl_state: OK")


def create_quota_daily_summary(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("summary_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("dag_run_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("units_search_list", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("units_channel_seed", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("units_videos_list", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("units_comment_threads", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("total_units_used", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("comments_collected", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("videos_discovered", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "quota_daily_summary")
    table.schema = schema
    table.description = "T04 — Tong hop YouTube API quota da dung moi ngay. Gioi han 10,000 units."
    client.create_table(table, exists_ok=True)
    print("quota_daily_summary: OK")


def create_quota_operation_log(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("log_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("dag_run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("operation_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("bucket", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("units_used", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("videos_processed", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("comments_collected", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("execution_time_seconds", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "quota_operation_log")
    table.schema = schema
    table.description = "T05 — Log chi tiet tung operation. Dung boi get_today_quota_used_by_bucket()."
    client.create_table(table, exists_ok=True)
    print("quota_operation_log: OK")


def run() -> None:
    client = get_client()
    create_channel_config(client)
    create_keyword_config(client)
    create_video_crawl_state(client)
    create_quota_daily_summary(client)
    create_quota_operation_log(client)
    print("\nLayer 0 — 5/5 tables created.")


if __name__ == "__main__":
    run()
