import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

def main():
    project_id = os.environ.get("GCP_PROJECT_ID")
    dataset = os.environ.get("BQ_DATASET")
    if not project_id or not dataset:
        print("Missing BQ credentials in .env")
        return
        
    client = bigquery.Client(project=project_id)
    
    for table_name in ["dim_products", "agg_daily_product_ranking", "causal_events", "fact_product_mentions"]:
        try:
            query = f"SELECT COUNT(1) AS cnt FROM `{project_id}.{dataset}.{table_name}`"
            rows = list(client.query(query).result())
            print(f"Table {table_name}: {rows[0].cnt} rows")
        except Exception as e:
            print(f"Table {table_name}: Error: {e}")

if __name__ == "__main__":
    main()
