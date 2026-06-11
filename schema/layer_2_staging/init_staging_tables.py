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


def create_stg_youtube_videos(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("keyword_matched", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("view_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("like_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("comment_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("data_quality_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("gcs_partition_date", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("_dbt_loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "stg_youtube_videos")
    table.schema = schema
    table.description = "T08 — dbt Staging: video da flatten tu raw_videos, co data_quality_score."
    client.create_table(table, exists_ok=True)
    print("stg_youtube_videos: OK")


def create_stg_youtube_comments(client: bigquery.Client) -> None:
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
        bigquery.SchemaField("data_quality_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("_dbt_loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "stg_youtube_comments")
    table.schema = schema
    table.description = "T09 — dbt Staging: comment da flatten, co is_reply flag va data_quality_score."
    client.create_table(table, exists_ok=True)
    print("stg_youtube_comments: OK")


def run() -> None:
    client = get_client()
    create_stg_youtube_videos(client)
    create_stg_youtube_comments(client)
    print("\nLayer 2 — 2/2 staging tables created.")


if __name__ == "__main__":
    run()
