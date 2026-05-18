"""
Bước 1 của NLP pipeline: Lấy câu từ BigQuery → annotation Gemini → lưu JSON.
Chạy: conda run -n etl-py313 python scratch/fetch_and_annotate_from_bq.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_OUTPUT = Path("data/export_for_colab/gemini_annotated_full.json")
_LIMIT = 2000
_MIN_WORDS = 5
_MIN_QUALITY = 0.8


def fetch_sentences() -> list[str]:
    from google.cloud import bigquery

    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ.get("BQ_DATASET", "sentiment_platform")
    client = bigquery.Client(project=project)

    query = f"""
        SELECT sentence_text
        FROM `{project}.{dataset}_intermediate.int_comment_sentences`
        WHERE sentence_text IS NOT NULL
          AND word_count >= {_MIN_WORDS}
          AND data_quality_score >= {_MIN_QUALITY}
        ORDER BY RAND()
        LIMIT {_LIMIT}
    """
    logger.info("Đang query BigQuery (limit=%d)...", _LIMIT)
    rows = client.query(query).result()
    sentences = [row.sentence_text for row in rows]
    logger.info("Lấy được %d câu từ BigQuery", len(sentences))
    return sentences


def main() -> None:
    sentences = fetch_sentences()
    if not sentences:
        logger.error("Không có câu nào từ BigQuery. Kiểm tra int_comment_sentences có data chưa.")
        sys.exit(1)

    from nlp.annotation.gemini_annotator import GeminiAnnotator

    # Tăng batch_size lên 150 câu/request để giảm tổng số request (chỉ tốn khoảng 14 requests cho 2000 câu)
    annotator = GeminiAnnotator(batch_size=210)
    logger.info("Bắt đầu annotation: %d câu / %d batch = %d requests Gemini",
                len(sentences), 210, -(-len(sentences) // 210))

    results = annotator.annotate_all(sentences)
    logger.info("Annotation xong: %d/%d câu thành công", len(results), len(sentences))

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("Đã lưu -> %s", _OUTPUT)
    logger.info("Bước tiếp theo: conda run -n etl-py313 python nlp/training/prepare_colab_data.py")


if __name__ == "__main__":
    main()
