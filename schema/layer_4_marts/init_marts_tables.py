import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]
MARTS_DATASET = f"{DATASET}_marts"


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def ensure_marts_dataset(client: bigquery.Client) -> None:
    dataset = bigquery.Dataset(f"{PROJECT_ID}.{MARTS_DATASET}")
    dataset.location = "asia-southeast1"
    client.create_dataset(dataset, exists_ok=True)


def table_ref(client: bigquery.Client, table_name: str) -> bigquery.Table:
    return bigquery.Table(f"{PROJECT_ID}.{MARTS_DATASET}.{table_name}")


def create_dim_products(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("brand", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("release_year", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("is_active", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "dim_products")
    table.schema = schema
    table.description = "T13 — dbt Marts: bang chieu san pham cong nghe. PK: product_id (slug brand-model)."
    client.create_table(table, exists_ok=True)
    print("dim_products: OK")


def create_fact_product_mentions(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("mention_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("result_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("aspect_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentiment_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("confidence_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("target_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_confidence", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("mention_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("_dbt_processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "fact_product_mentions")
    table.schema = schema
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="mention_date",
    )
    table.clustering_fields = ["product_id", "aspect_label", "sentiment_label"]
    table.description = (
        "T14 — dbt Marts: fact table trung tam. "
        "1 row = 1 lan san pham duoc nhac den voi 1 khia canh va 1 cam xuc. "
        "Partition theo mention_date, cluster theo product_id."
    )
    client.create_table(table, exists_ok=True)
    print("fact_product_mentions: OK")


def create_agg_daily_product_ranking(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("ranking_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ranking_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("bayesian_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("controversy_index", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("controversy_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("total_mentions", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("positive_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("negative_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("neutral_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("excluded_none_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("top_aspect", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sentiment_trend", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("rank_position", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("_dbt_processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "agg_daily_product_ranking")
    table.schema = schema
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="ranking_date",
    )
    table.clustering_fields = ["category", "product_id"]
    table.description = (
        "T15 — dbt Marts: xep hang hang ngay theo Bayesian Score + Controversy Index. "
        "Nguon du lieu chinh cho FastAPI /ranking va Streamlit Tab 1."
    )
    client.create_table(table, exists_ok=True)
    print("agg_daily_product_ranking: OK")


def create_causal_events(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("change_point_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("event_video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("event_video_title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("event_view_count", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("temporal_proximity", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("direction_alignment", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("attribution_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("sentiment_direction", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("explanation_text", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("generated_by", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("detected_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "causal_events")
    table.schema = schema
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="change_point_date",
    )
    table.clustering_fields = ["product_id"]
    table.description = (
        "T16 — dbt Marts: ket qua PELT (ruptures). "
        "Moi row = 1 su kien tuong quan voi bien dong sentiment. "
        "Giai thich bang tieng Viet do Gemini Flash sinh ra."
    )
    client.create_table(table, exists_ok=True)
    print("causal_events: OK")


def run() -> None:
    client = get_client()
    ensure_marts_dataset(client)
    create_dim_products(client)
    create_fact_product_mentions(client)
    create_agg_daily_product_ranking(client)
    create_causal_events(client)
    print("\nLayer 4 — 4/4 marts tables created.")


if __name__ == "__main__":
    run()
