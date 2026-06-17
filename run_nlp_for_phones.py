import os
import logging
from nlp.runner import _DEFAULT_LIMIT, build_result_rows, _run_and_write_bq_batches, _utc_now_iso, _chunks, _build_rows_for_annotations, write_rows_to_bigquery_with_retry, load_nlp_config
from nlp.inference.confidence_router import ConfidenceRouter
from tqdm import tqdm as progress_bar

logger = logging.getLogger(__name__)

def custom_fetch(limit, reprocess=False):
    from google.cloud import bigquery
    from nlp.schemas import SentenceRecord
    project_id = os.environ["GCP_PROJECT_ID"]
    base_dataset = os.environ["BQ_DATASET"]
    dataset = f"{base_dataset}_intermediate"
    client = bigquery.Client(project=project_id)
    
    query = f"""
        SELECT
          s.sentence_id,
          s.comment_id,
          s.video_id,
          COALESCE(NULLIF(s.sentence_text_normalized, ''), s.sentence_text) AS sentence_text
        FROM `{project_id}.{dataset}.int_comment_sentences` s
        LEFT JOIN `{project_id}.{dataset}.int_sentiment_results` int_results
          ON s.sentence_id = int_results.sentence_id
        LEFT JOIN `{project_id}.{base_dataset}.raw_sentiment_results` raw_results
          ON s.sentence_id = raw_results.sentence_id
        WHERE s.is_vietnamese = TRUE
          AND int_results.sentence_id IS NULL
          AND raw_results.sentence_id IS NULL
          AND s.video_id IN (
            SELECT v.video_id
            FROM `{project_id}.{base_dataset}.raw_videos` v
            JOIN `{project_id}.{base_dataset}.keyword_config` k ON v.keyword_id = k.keyword_id
            WHERE k.product_id IN ('iphone-11', 'iphone-12', 'xiaomi-11-pro')
          )
    """
    logger.info("Executing custom fetch query...")
    rows = list(client.query(query).result())
    return [SentenceRecord(**dict(row)) for row in rows]

def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    records = custom_fetch(0)
    logger.info(f"Running NLP inference for {len(records)} sentences for the 3 phones...")
    if not records:
        return
    router = ConfidenceRouter()
    dag_run_id = "manual-pelt-3phones"
    with progress_bar(total=len(records), desc="NLP inference", unit="sentence") as progress:
        _run_and_write_bq_batches(
            records,
            router,
            dag_run_id,
            load_nlp_config(),
            progress=progress,
        )

if __name__ == "__main__":
    run()
