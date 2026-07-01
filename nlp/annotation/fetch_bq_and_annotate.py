import argparse
import json
import logging
import sys
from pathlib import Path

# Thêm thư mục gốc của dự án vào sys.path để tránh lỗi ModuleNotFoundError
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.cloud import bigquery

from elt.config import load_config
from nlp.annotation.gemini_annotator import GeminiAnnotator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

def fetch_bq_and_annotate(limit: int = 1500, checkpoint_file: Path | None = None):
    # 1. Tải cấu hình
    config = load_config()
    bq_client = bigquery.Client(project=config.gcp.project_id)
    dataset = config.gcp.dataset
    table_id = f"{config.gcp.project_id}.{dataset}.raw_comments"

    # 2. Truy vấn BigQuery lấy các comment có khả năng cao là Positive/Negative
    # Loại bỏ các bình luận quá ngắn hoặc quá dài.
    query = f"""
        SELECT DISTINCT text_original 
        FROM `{table_id}`
        WHERE LENGTH(text_original) BETWEEN 20 AND 300
          AND (
            LOWER(text_original) LIKE '%pin%' OR 
            LOWER(text_original) LIKE '%sạc%' OR 
            LOWER(text_original) LIKE '%camera%' OR 
            LOWER(text_original) LIKE '%chụp%' OR
            LOWER(text_original) LIKE '%màn hình%' OR
            LOWER(text_original) LIKE '%hiển thị%' OR
            LOWER(text_original) LIKE '%hiệu năng%' OR
            LOWER(text_original) LIKE '%chơi game%' OR 
            LOWER(text_original) LIKE '%lag%' OR 
            LOWER(text_original) LIKE '%mượt%' OR 
            LOWER(text_original) LIKE '%thiết kế%' OR
            LOWER(text_original) LIKE '%ngoại hình%' OR
            LOWER(text_original) LIKE '%cầm nắm%' OR
            LOWER(text_original) LIKE '%giá%' OR
            LOWER(text_original) LIKE '%đắt%' OR
            LOWER(text_original) LIKE '%rẻ%' OR
            LOWER(text_original) LIKE '%đáng tiền%'
          )
        ORDER BY RAND()
        LIMIT {limit}
    """
    logger.info("Executing BigQuery fetch...")
    query_job = bq_client.query(query)
    rows = query_job.result()
    
    sentences = [row.text_original for row in rows if row.text_original]
    logger.info(f"Fetched {len(sentences)} potential Pos/Neg sentences from BigQuery.")

    if not sentences:
        logger.warning("No sentences found. Check your BigQuery table and filters.")
        return

    # 3. Chạy Gemini Annotator
    annotator = GeminiAnnotator(batch_size=50)
    
    if not checkpoint_file:
        root = Path(__file__).parent.parent.parent / "data" / "export_for_colab"
        root.mkdir(parents=True, exist_ok=True)
        checkpoint_file = root / "gemini_annotated_pos_neg.json"
        
    logger.info(f"Starting annotation. Checkpoint file: {checkpoint_file}")
    results = annotator.annotate_all(sentences, checkpoint_file=checkpoint_file)
    
    logger.info(f"Annotation complete! Total valid annotated records: {len(results)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1500, help="Số lượng bình luận cần trích xuất")
    args = parser.parse_args()
    
    fetch_bq_and_annotate(limit=args.limit)
