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


def create_int_comment_sentences(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("sentence_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_index", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("sentence_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_text_normalized", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("is_vietnamese", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("word_count", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("data_quality_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("_dbt_processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "int_comment_sentences")
    table.schema = schema
    table.description = (
        "T10 — dbt Intermediate: comment tach thanh cau — don vi NLP nho nhat. "
        "Input cho vELECTRA + PhoBERT."
    )
    client.create_table(table, exists_ok=True)
    print("int_comment_sentences: OK")


def create_int_sentiment_results(client: bigquery.Client) -> None:
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
    table = table_ref(client, "int_sentiment_results")
    table.schema = schema
    table.description = (
        "T11 — dbt Intermediate: ket qua NLP. vELECTRA trich xuat aspect, "
        "PhoBERT phan loai cam xuc. Gemini fallback khi confidence < 0.70."
    )
    client.create_table(table, exists_ok=True)
    print("int_sentiment_results: OK")


def create_finetune_dataset(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("sample_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentence_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("tokens_json", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("bio_tags_json", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("aspect_labels_json", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sentiment_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("annotation_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("split", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("is_validated", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("annotated_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "finetune_dataset")
    table.schema = schema
    table.description = (
        "T12 — dbt Intermediate: dataset BIO-tagged do Gemini auto-annotate. "
        "Dung de fine-tune vELECTRA. Co the publish len HuggingFace Hub."
    )
    client.create_table(table, exists_ok=True)
    print("finetune_dataset: OK")


def create_int_video_product_mentions(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("role", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("match_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("confidence_score", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("_dbt_processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "int_video_product_mentions")
    table.schema = schema
    table.description = "Resolved product models found in video title and description."
    client.create_table(table, exists_ok=True)
    print("int_video_product_mentions: OK")


def create_int_sentence_product_targets(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("sentence_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_confidence", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("target_sentiment_label", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("resolution_status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("_dbt_processed_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "int_sentence_product_targets")
    table.schema = schema
    table.description = "Product target resolution per comment sentence. Ambiguous targets wait for LLM fallback."
    client.create_table(table, exists_ok=True)
    print("int_sentence_product_targets: OK")


def create_int_product_resolution_candidates(client: bigquery.Client) -> None:
    schema = [
        bigquery.SchemaField("candidate_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("candidate_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("resolved_product_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = table_ref(client, "int_product_resolution_candidates")
    table.schema = schema
    table.description = "Computed unresolved video and sentence candidates waiting for admin or LLM resolution."
    client.create_table(table, exists_ok=True)
    print("int_product_resolution_candidates: OK")


def run() -> None:
    client = get_client()
    create_int_comment_sentences(client)
    create_int_sentiment_results(client)
    create_finetune_dataset(client)
    create_int_video_product_mentions(client)
    create_int_sentence_product_targets(client)
    create_int_product_resolution_candidates(client)
    print("\nLayer 3 — 6/6 intermediate tables created.")


if __name__ == "__main__":
    run()
