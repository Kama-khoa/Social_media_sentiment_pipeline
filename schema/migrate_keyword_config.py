"""
Migration: thêm cột last_updated_at vào keyword_config.
Chạy 1 lần trước khi dùng Admin CRUD keyword endpoints.

    conda activate etl-py313
    python schema/migrate_keyword_config.py
"""
import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]


def run() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    sql = f"""
        ALTER TABLE `{PROJECT_ID}.{DATASET}.keyword_config`
        ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMP
    """
    client.query(sql).result()
    print("keyword_config: last_updated_at column added (or already existed).")


if __name__ == "__main__":
    run()
