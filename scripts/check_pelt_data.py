import os
import sys
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# Force standard output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    project_id = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ["BQ_DATASET"]
    client = bigquery.Client(project=project_id)
    
    # 1. Check int_sentiment_results
    query_sr = f"""
        SELECT COUNT(*) as cnt
        FROM `{project_id}.{dataset}_intermediate.int_sentiment_results`
        WHERE video_id IN (
            SELECT video_id FROM `{project_id}.{dataset}_intermediate.int_video_product_mentions`
            WHERE product_id = 'iphone-16-pro'
        )
    """
    print("--- int_sentiment_results ---")
    rows_sr = list(client.query(query_sr).result())
    print(f"Rows in int_sentiment_results for iphone-16-pro videos: {rows_sr[0].cnt if rows_sr else 0}")

    # 2. Check int_sentence_product_targets
    query_t = f"""
        SELECT resolution_status, COUNT(*) as cnt
        FROM `{project_id}.{dataset}_intermediate.int_sentence_product_targets`
        WHERE product_id = 'iphone-16-pro'
        GROUP BY resolution_status
    """
    print("\n--- int_sentence_product_targets (iphone-16-pro) ---")
    rows_t = list(client.query(query_t).result())
    if rows_t:
        for r in rows_t:
            print(f"Status: {r.resolution_status} | Count: {r.cnt}")
    else:
        print("No targets found for iphone-16-pro in int_sentence_product_targets!")

    # 3. Check general unresolved sentences
    query_unresolved = f"""
        SELECT COUNT(*) as cnt
        FROM `{project_id}.{dataset}_intermediate.int_product_resolution_candidates`
    """
    print("\n--- int_product_resolution_candidates (all) ---")
    rows_c = list(client.query(query_unresolved).result())
    print(f"Total rows in int_product_resolution_candidates: {rows_c[0].cnt if rows_c else 0}")

if __name__ == "__main__":
    main()
