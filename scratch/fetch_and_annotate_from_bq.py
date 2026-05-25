"""
Bước 1 của NLP pipeline: Lấy câu từ BigQuery → annotation Gemini → lưu JSON.

Chạy:
  conda run -n etl-py313 python scratch/fetch_and_annotate_from_bq.py

Tuỳ chọn:
  --limit N           Số câu tối đa sau post-processing (mặc định 2000)
  --batch-size N      Số câu mỗi request Gemini (mặc định 20)
  --min-words N       Số từ tối thiểu theo SPLIT(' ') (mặc định 5)
  --min-quality F     Điểm chất lượng tối thiểu 0-1 (mặc định 0.8)
  --aspect-ratio F    Tỷ lệ câu Pool A có keyword aspect (mặc định 0.7)
  --output PATH       Đường dẫn file output/checkpoint JSON
"""
from __future__ import annotations

import argparse
import logging
import math
import os
import re
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path("data/export_for_colab/gemini_annotated_full.json")
_DEFAULT_LIMIT = 2000
_DEFAULT_BATCH_SIZE = 20
_DEFAULT_MIN_WORDS = 5
_DEFAULT_MIN_QUALITY = 0.8
_DEFAULT_ASPECT_RATIO = 0.7

_MIN_CHARS = 15
_MAX_CHARS = 300

# Regex nhận diện ít nhất 1 ký tự có dấu tiếng Việt
_VN_DIACRITIC = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]"
)

# Keyword regex cho 6 aspect label — dùng để chia Pool A / Pool B trong BQ
_ASPECT_KEYWORD_REGEX = (
    r"pin|sạc|battery|camera|chụp|ảnh|quay|zoom|selfie"
    r"|màn.?hình|screen|display|amoled|oled"
    r"|hiệu.?năng|lag|giật|chip|cpu|ram|snapdragon|dimensity|xử.?lý"
    r"|thiết.?kế|kiểu.?dáng|mỏng|nặng|mặt.?lưng|cầm"
    r"|giá|mua|bán|tiền|triệu|nghìn|rẻ|đắt|tầm.?tiền"
)

# Tham chiếu RPM model ưu tiên để tính ước tính thời gian
_PRIMARY_MODEL_RPM = 30
_SAFETY_FACTOR = 0.75
_PRIMARY_RPD = 1500


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch sentences from BQ and annotate with Gemini"
    )
    parser.add_argument("--limit", type=int, default=_DEFAULT_LIMIT)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--min-words", type=int, default=_DEFAULT_MIN_WORDS)
    parser.add_argument("--min-quality", type=float, default=_DEFAULT_MIN_QUALITY)
    parser.add_argument(
        "--aspect-ratio",
        type=float,
        default=_DEFAULT_ASPECT_RATIO,
        help="Tỷ lệ câu Pool A (có keyword aspect) so với tổng (0-1, default 0.7)",
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser.parse_args()


def fetch_sentences(
    limit: int,
    min_words: int,
    min_quality: float,
    aspect_ratio: float,
) -> tuple[list[str], dict]:
    from google.cloud import bigquery

    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ.get("BQ_DATASET", "sentiment_platform")
    client = bigquery.Client(project=project)

    # Fetch dư 30% so với limit để bù cho post-processing loại bớt
    fetch_limit = int(limit * 1.3)
    keyword_limit = int(fetch_limit * aspect_ratio)
    generic_limit = fetch_limit - keyword_limit

    query = f"""
        WITH filtered AS (
            SELECT sentence_text
            FROM `{project}.{dataset}_intermediate.int_comment_sentences`
            WHERE sentence_text IS NOT NULL
              AND word_count >= {min_words}
              AND data_quality_score >= {min_quality}
              AND LENGTH(sentence_text) >= {_MIN_CHARS}
              AND NOT REGEXP_CONTAINS(sentence_text, r'(?i)https?://|www\\.')
        ),
        aspect_hinted AS (
            SELECT sentence_text
            FROM filtered
            WHERE REGEXP_CONTAINS(LOWER(sentence_text), r'{_ASPECT_KEYWORD_REGEX}')
            ORDER BY RAND()
            LIMIT {keyword_limit}
        ),
        generic AS (
            SELECT sentence_text
            FROM filtered
            WHERE NOT REGEXP_CONTAINS(LOWER(sentence_text), r'{_ASPECT_KEYWORD_REGEX}')
            ORDER BY RAND()
            LIMIT {generic_limit}
        )
        SELECT sentence_text FROM aspect_hinted
        UNION ALL
        SELECT sentence_text FROM generic
        ORDER BY RAND()
    """

    logger.info(
        "Query BQ: fetch_limit=%d (Pool A aspect_hinted=%d, Pool B generic=%d)...",
        fetch_limit, keyword_limit, generic_limit,
    )
    rows = client.query(query).result()
    sentences = [row.sentence_text for row in rows]

    bq_stats = {
        "bq_total": len(sentences),
        "pool_a_target": keyword_limit,
        "pool_b_target": generic_limit,
    }
    logger.info("BQ trả về %d câu", len(sentences))
    return sentences, bq_stats


def _filter_quality(sentences: list[str]) -> tuple[list[str], dict]:
    from nlp.embeddings.text_normalizer import TextNormalizer

    seen_hashes: set[str] = set()
    result: list[str] = []
    stats = {"no_vn": 0, "duplicate": 0, "length": 0}

    for s in sentences:
        if not (_MIN_CHARS <= len(s) <= _MAX_CHARS):
            stats["length"] += 1
            continue
        if not _VN_DIACRITIC.search(s.lower()):
            stats["no_vn"] += 1
            continue
        h = TextNormalizer.generate_hash(s)
        if h in seen_hashes:
            stats["duplicate"] += 1
            continue
        seen_hashes.add(h)
        result.append(s)

    return result, stats


def _log_fetch_stats(
    bq_stats: dict,
    filter_stats: dict,
    final_sentences: list[str],
    batch_size: int,
    output: Path,
) -> None:
    import json

    already_done = 0
    if output.exists():
        try:
            with open(output, encoding="utf-8") as f:
                data = json.load(f)
            already_done = len({r["sentence"] for r in data})
        except Exception:
            pass

    lengths = [len(s) for s in final_sentences]
    pending = max(0, len(final_sentences) - already_done)
    total_batches = math.ceil(pending / batch_size)
    effective_rpm = _PRIMARY_MODEL_RPM * _SAFETY_FACTOR
    estimated_mins = (total_batches * 60.0 / effective_rpm) / 60

    logger.info(
        "=== Fetch & Quality Stats ===\n"
        "  BQ trả về              : %d câu\n"
        "  Loại do length ngoài [%d-%d]  : %d\n"
        "  Loại do không dấu tiếng Việt: %d\n"
        "  Loại do trùng lặp      : %d\n"
        "  Còn lại sau filter     : %d câu\n"
        "  Đã có trong checkpoint : %d câu\n"
        "  Cần annotation (pending): %d câu\n"
        "  Char length [min/median/max]: %d / %d / %d\n"
        "  Tổng requests Gemini   : %d\n"
        "  RPM hiệu quả (75%% limit): %.1f RPM\n"
        "  Thời gian ước tính     : ~%.1f phút\n"
        "  Output                 : %s",
        bq_stats["bq_total"],
        _MIN_CHARS, _MAX_CHARS, filter_stats["length"],
        filter_stats["no_vn"],
        filter_stats["duplicate"],
        len(final_sentences),
        already_done,
        pending,
        min(lengths) if lengths else 0,
        int(median(lengths)) if lengths else 0,
        max(lengths) if lengths else 0,
        total_batches,
        effective_rpm,
        estimated_mins,
        output,
    )

    if total_batches > _PRIMARY_RPD:
        logger.warning(
            "Số request (%d) vượt RPD của model ưu tiên (%d). "
            "Pipeline sẽ tự động fallback sang model khác.",
            total_batches, _PRIMARY_RPD,
        )


def main() -> None:
    args = _parse_args()

    if not (0.0 < args.aspect_ratio < 1.0):
        logger.error("--aspect-ratio phải trong khoảng (0, 1), nhận được: %s", args.aspect_ratio)
        sys.exit(1)

    raw_sentences, bq_stats = fetch_sentences(
        args.limit, args.min_words, args.min_quality, args.aspect_ratio
    )
    if not raw_sentences:
        logger.error("Không có câu nào từ BigQuery. Kiểm tra int_comment_sentences có data chưa.")
        sys.exit(1)

    sentences, filter_stats = _filter_quality(raw_sentences)
    sentences = sentences[: args.limit]

    if not sentences:
        logger.error("Không còn câu nào sau quality filter. Thử giảm --min-quality hoặc --min-words.")
        sys.exit(1)

    _log_fetch_stats(bq_stats, filter_stats, sentences, args.batch_size, args.output)

    from nlp.annotation.gemini_annotator import GeminiAnnotator

    annotator = GeminiAnnotator(batch_size=args.batch_size)
    total_batches = math.ceil(len(sentences) / args.batch_size)
    logger.info(
        "Bắt đầu annotation: %d câu / batch=%d = %d requests → %s",
        len(sentences), args.batch_size, total_batches, args.output,
    )

    results = annotator.annotate_all(sentences, checkpoint_file=args.output)
    logger.info("Annotation xong: %d items từ %d câu", len(results), len(sentences))
    logger.info("Bước tiếp theo: conda run -n etl-py313 python nlp/training/prepare_colab_data.py")


if __name__ == "__main__":
    main()
