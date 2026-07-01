"""
Migration: thêm cột needs_backfill vào keyword_config.
Chạy 1 lần để hỗ trợ cơ chế tự động backfill lịch sử từ khóa sản phẩm mới.

    conda activate etl-py313
    python schema/migrate_keyword_config_backfill.py
"""
import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]


def run() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    
    # 1. Thêm cột needs_backfill
    sql_add = f"""
        ALTER TABLE `{PROJECT_ID}.{DATASET}.keyword_config`
        ADD COLUMN IF NOT EXISTS needs_backfill BOOL
    """
    client.query(sql_add).result()
    print("keyword_config: needs_backfill column added (or already existed).")
    
    # 2. Cập nhật các từ khóa cũ thành FALSE để tránh cào lại lịch sử toàn bộ hệ thống
    sql_update = f"""
        UPDATE `{PROJECT_ID}.{DATASET}.keyword_config`
        SET needs_backfill = FALSE
        WHERE needs_backfill IS NULL
    """
    client.query(sql_update).result()
    print("keyword_config: updated existing keywords needs_backfill = FALSE.")


if __name__ == "__main__":
    run()
