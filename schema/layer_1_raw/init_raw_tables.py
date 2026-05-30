import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]
GCS_BUCKET = os.environ["GCS_BUCKET_NAME"]


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def create_raw_videos_external(client: bigquery.Client) -> None:
    table_id = f"{PROJECT_ID}.{DATASET}.raw_videos"

    external_config = bigquery.ExternalConfig("NEWLINE_DELIMITED_JSON")
    external_config.source_uris = [
        f"gs://{GCS_BUCKET}/raw/youtube/*/videos/*.json"
    ]
    external_config.autodetect = False

    hive_config = bigquery.HivePartitioningOptions()
    hive_config.mode = "CUSTOM"
    hive_config.source_uri_prefix = f"gs://{GCS_BUCKET}/raw/youtube/{{gcs_partition_date:STRING}}/videos/"
    external_config.hive_partitioning = hive_config

    schema = [
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("view_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("like_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("comment_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("duration_seconds", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
        bigquery.SchemaField("thumbnail_url", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("search_mode", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("keyword_matched", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("gcs_partition_date", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("crawled_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    external_config.schema = schema

    table = bigquery.Table(table_id)
    table.external_data_configuration = external_config
    table.description = "T06 — External Table: metadata video tho tu GCS. Partition theo gcs_partition_date."

    existing_tables = [t.table_id for t in client.list_tables(DATASET)]
    if "raw_videos" in existing_tables:
        print("raw_videos: already exists, skipping.")
        return

    client.create_table(table)
    print("raw_videos: OK")


def create_raw_comments_external(client: bigquery.Client) -> None:
    table_id = f"{PROJECT_ID}.{DATASET}.raw_comments"

    external_config = bigquery.ExternalConfig("NEWLINE_DELIMITED_JSON")
    external_config.source_uris = [
        f"gs://{GCS_BUCKET}/raw/youtube/*/comments/*.json"
    ]
    external_config.autodetect = False

    hive_config = bigquery.HivePartitioningOptions()
    hive_config.mode = "CUSTOM"
    hive_config.source_uri_prefix = f"gs://{GCS_BUCKET}/raw/youtube/{{gcs_partition_date:STRING}}/comments/"
    external_config.hive_partitioning = hive_config

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
    external_config.schema = schema

    table = bigquery.Table(table_id)
    table.external_data_configuration = external_config
    table.description = "T07 — External Table: binh luan tho tu GCS. 0 YouTube API quota (youtube-comment-downloader)."

    existing_tables = [t.table_id for t in client.list_tables(DATASET)]
    if "raw_comments" in existing_tables:
        print("raw_comments: already exists, skipping.")
        return

    client.create_table(table)
    print("raw_comments: OK")


def create_raw_sentiment_results(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("result_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("aspect_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("segment_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentiment_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("confidence_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("inference_model", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("dag_run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = bigquery.Table(f"{PROJECT_ID}.{DATASET}.raw_sentiment_results", schema=schema)
    table.description = (
        "T08 - Raw NLP inference results written by nlp.runner. "
        "dbt promotes this table to intermediate.int_sentiment_results."
    )
    client.create_table(table, exists_ok=True)
    print("raw_sentiment_results: OK")


def run() -> None:
    client = get_client()
    create_raw_videos_external(client)
    create_raw_comments_external(client)
    create_raw_sentiment_results(client)
    print("\nLayer 1 — 2/2 external tables created.")


if __name__ == "__main__":
    run()
