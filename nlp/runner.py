from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TypeVar

from dotenv import load_dotenv

from nlp.config import NLPConfig, load_nlp_config
from nlp.inference.confidence_router import ConfidenceRouter
from pipeline_progress import progress_bar

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 500
_DEFAULT_DAG_RUN_ID = "manual"
_MODEL_NAME = "velectra_aspect+phobert_sentiment"
_FAILED_BATCH_LOG_DIR = Path("logs") / "nlp_failed_batches"
_RESULT_COLUMNS = [
    "result_id",
    "sentence_id",
    "comment_id",
    "video_id",
    "aspect_label",
    "segment_text",
    "sentiment_label",
    "confidence_score",
    "inference_model",
    "dag_run_id",
    "processed_at",
]
_T = TypeVar("_T")


@dataclass(frozen=True)
class SentenceRecord:
    sentence_id: str
    comment_id: str
    video_id: str
    sentence_text: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_id(sentence_id: str, aspect_label: str, segment_text: str) -> str:
    raw = f"{sentence_id}|{aspect_label}|{segment_text}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _normalize_sentence_record(row: dict) -> SentenceRecord:
    sentence_text = (
        row.get("sentence_text_normalized")
        or row.get("sentence_text")
        or row.get("text")
        or ""
    )
    return SentenceRecord(
        sentence_id=str(row["sentence_id"]),
        comment_id=str(row["comment_id"]),
        video_id=str(row["video_id"]),
        sentence_text=str(sentence_text),
    )


def rows_from_jsonl(path: Path) -> list[SentenceRecord]:
    records: list[SentenceRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(_normalize_sentence_record(json.loads(line)))
    return records


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _chunks(items: list[_T], batch_size: int) -> Iterable[list[_T]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def _build_rows_for_annotations(
    record_annotations: Iterable[tuple[SentenceRecord, list[dict]]],
    dag_run_id: str,
    processed_at: str,
) -> list[dict]:
    output: list[dict] = []
    for record, annotations in record_annotations:
        for item in annotations:
            aspect_label = str(item["aspect_label"])
            segment_text = str(item.get("segment_text", ""))
            source = str(item.get("source", "model"))
            confidence = float(item.get("confidence", 1.0 if source == "gemini" else 0.0))
            output.append({
                "result_id": _result_id(record.sentence_id, aspect_label, segment_text),
                "sentence_id": record.sentence_id,
                "comment_id": record.comment_id,
                "video_id": record.video_id,
                "aspect_label": aspect_label,
                "segment_text": segment_text,
                "sentiment_label": str(item["sentiment_label"]),
                "confidence_score": confidence,
                "inference_model": (
                    _MODEL_NAME if source == "model" else "gemini_fallback"
                ),
                "dag_run_id": dag_run_id,
                "processed_at": processed_at,
            })
    return output


def build_result_rows(
    records: Iterable[SentenceRecord],
    router: ConfidenceRouter,
    dag_run_id: str = _DEFAULT_DAG_RUN_ID,
    processed_at: str | None = None,
) -> list[dict]:
    processed_at = processed_at or _utc_now_iso()
    records = list(records)
    annotations_by_record = router.annotate_many(
        [record.sentence_text for record in records]
    )
    record_annotations: list[tuple[SentenceRecord, list[dict]]] = []
    missing_count = 0

    for record, annotations in zip(records, annotations_by_record):
        if not annotations:
            missing_count += 1
            continue
        record_annotations.append((record, annotations))

    if missing_count:
        logger.warning(
            "Skipped %d sentences without annotations; they will be retried on a later run",
            missing_count,
        )
    return _build_rows_for_annotations(record_annotations, dag_run_id, processed_at)


def build_local_debug_rows(
    records: Iterable[SentenceRecord],
    router: ConfidenceRouter,
) -> list[dict]:
    output: list[dict] = []
    for record in records:
        diagnostics = router.diagnose_local(record.sentence_text)
        for item in diagnostics:
            output.append({
                "sentence_id": record.sentence_id,
                "comment_id": record.comment_id,
                "video_id": record.video_id,
                "sentence_text": record.sentence_text,
                "aspect_label": item["aspect_label"],
                "segment_text": item["segment_text"],
                "sentiment_label": item["sentiment_label"],
                "ner_confidence": item["ner_confidence"],
                "sentiment_confidence": item["sentiment_confidence"],
                "confidence": item["confidence"],
                "would_fallback": item["would_fallback"],
                "fallback_reason": item["fallback_reason"],
            })
    return output


def log_debug_summary(rows: list[dict]) -> None:
    if not rows:
        logger.info("Local confidence debug: no rows")
        return

    fallback_rows = [row for row in rows if row["would_fallback"]]
    by_reason: dict[str, int] = {}
    for row in fallback_rows:
        reason = row["fallback_reason"] or "accepted"
        by_reason[reason] = by_reason.get(reason, 0) + 1

    logger.info(
        "Local confidence debug: %d/%d aspect rows would fallback (%.1f%%)",
        len(fallback_rows),
        len(rows),
        100 * len(fallback_rows) / len(rows),
    )
    for reason, count in sorted(by_reason.items()):
        logger.info("Fallback reason [%s]: %d", reason, count)


def _intermediate_dataset(base_dataset: str) -> str:
    return os.environ.get("BQ_INTERMEDIATE_DATASET", f"{base_dataset}_intermediate")


def fetch_unprocessed_sentences(limit: int, reprocess: bool = False) -> list[SentenceRecord]:
    from google.cloud import bigquery

    project_id = os.environ["GCP_PROJECT_ID"]
    base_dataset = os.environ["BQ_DATASET"]
    dataset = _intermediate_dataset(base_dataset)
    client = bigquery.Client(project=project_id)
    limit_clause = ""
    query_parameters = []
    if limit > 0:
        limit_clause = "LIMIT @limit"
        query_parameters.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))

    processed_filter = ""
    processed_joins = ""
    if not reprocess:
        processed_joins = f"""
        LEFT JOIN `{project_id}.{dataset}.int_sentiment_results` int_results
          ON s.sentence_id = int_results.sentence_id
        LEFT JOIN `{project_id}.{base_dataset}.raw_sentiment_results` raw_results
          ON s.sentence_id = raw_results.sentence_id
        """
        processed_filter = """
          AND int_results.sentence_id IS NULL
          AND raw_results.sentence_id IS NULL
        """

    query = f"""
        SELECT
          s.sentence_id,
          s.comment_id,
          s.video_id,
          COALESCE(NULLIF(s.sentence_text_normalized, ''), s.sentence_text) AS sentence_text
        FROM `{project_id}.{dataset}.int_comment_sentences` s
        {processed_joins}
        WHERE 1 = 1
          {processed_filter}
          AND s.is_vietnamese = TRUE
          AND s.data_quality_score >= 0.8
          AND s.word_count BETWEEN 2 AND 80
        ORDER BY s.published_at DESC
        {limit_clause}
    """
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    rows = client.query(query, job_config=job_config).result()
    return [_normalize_sentence_record(dict(row.items())) for row in rows]


def _raw_results_schema():
    from google.cloud import bigquery

    return [
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


def _build_merge_sql(target_table: str, staging_table: str) -> str:
    update_assignments = ",\n          ".join(
        f"{column} = S.{column}" for column in _RESULT_COLUMNS if column != "result_id"
    )
    insert_columns = ", ".join(_RESULT_COLUMNS)
    insert_values = ", ".join(f"S.{column}" for column in _RESULT_COLUMNS)
    return f"""
        MERGE `{target_table}` T
        USING `{staging_table}` S
        ON T.result_id = S.result_id
        WHEN MATCHED THEN UPDATE SET
          {update_assignments}
        WHEN NOT MATCHED THEN INSERT ({insert_columns})
        VALUES ({insert_values})
    """


def write_rows_to_bigquery(rows: list[dict]) -> None:
    if not rows:
        return

    from google.cloud import bigquery

    project_id = os.environ["GCP_PROJECT_ID"]
    base_dataset = os.environ["BQ_DATASET"]
    client = bigquery.Client(project=project_id)
    target_table = f"{project_id}.{base_dataset}.raw_sentiment_results"
    staging_table = (
        f"{project_id}.{base_dataset}."
        f"_raw_sentiment_results_stage_{uuid.uuid4().hex[:12]}"
    )

    job_config = bigquery.LoadJobConfig(
        schema=_raw_results_schema(),
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    try:
        load_job = client.load_table_from_json(rows, staging_table, job_config=job_config)
        load_job.result()
        client.query(_build_merge_sql(target_table, staging_table)).result()
    finally:
        client.delete_table(staging_table, not_found_ok=True)


def _failed_batch_log_path(dag_run_id: str) -> Path:
    safe_run_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", dag_run_id).strip("._")
    return _FAILED_BATCH_LOG_DIR / f"{safe_run_id or 'unknown_run'}.jsonl"


def _log_failed_bq_batch(
    *,
    rows: list[dict],
    dag_run_id: str,
    batch_index: int,
    phase: str,
    attempts: int,
    error: Exception,
) -> None:
    payload = {
        "timestamp": _utc_now_iso(),
        "dag_run_id": dag_run_id,
        "batch_index": batch_index,
        "phase": phase,
        "sentence_ids": sorted({str(row["sentence_id"]) for row in rows}),
        "attempts": attempts,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "rows": rows,
    }
    path = _failed_batch_log_path(dag_run_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("Could not write failed NLP batch log to %s", path)


def write_rows_to_bigquery_with_retry(
    rows: list[dict],
    *,
    dag_run_id: str,
    batch_index: int,
    phase: str,
    max_retries: int,
    retry_base_seconds: float,
) -> bool:
    if not rows:
        return True

    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            write_rows_to_bigquery(rows)
            return True
        except Exception as exc:
            if attempt < attempts:
                delay = retry_base_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "BigQuery write batch %d [%s] attempt %d/%d failed: %s. "
                    "Retrying in %.1fs",
                    batch_index,
                    phase,
                    attempt,
                    attempts,
                    exc,
                    delay,
                )
                time.sleep(delay)
                continue

            logger.error(
                "Skipping BigQuery write batch %d [%s] after %d attempts: %s",
                batch_index,
                phase,
                attempts,
                exc,
            )
            _log_failed_bq_batch(
                rows=rows,
                dag_run_id=dag_run_id,
                batch_index=batch_index,
                phase=phase,
                attempts=attempts,
                error=exc,
            )
            return False

    return False


@dataclass
class _BatchWriteStats:
    committed_batches: int = 0
    skipped_batches: int = 0
    unresolved_sentences: int = 0


def _run_and_write_bq_batches(
    records: list[SentenceRecord],
    router: ConfidenceRouter,
    dag_run_id: str,
    config: NLPConfig,
    progress=None,
) -> list[dict]:
    processed_at = _utc_now_iso()
    output: list[dict] = []
    record_order = {record.sentence_id: index for index, record in enumerate(records)}
    pending_fallback: dict[str, list[SentenceRecord]] = defaultdict(list)
    gemini_cache: dict[str, list[dict]] = {}
    stats = _BatchWriteStats()
    write_batch_index = 0

    def persist(
        record_annotations: list[tuple[SentenceRecord, list[dict]]],
        phase: str,
    ) -> None:
        nonlocal write_batch_index
        for pair_batch in _chunks(record_annotations, config.bq_write_batch_size):
            rows = _build_rows_for_annotations(pair_batch, dag_run_id, processed_at)
            output.extend(rows)
            if not rows:
                continue
            write_batch_index += 1
            if write_rows_to_bigquery_with_retry(
                rows,
                dag_run_id=dag_run_id,
                batch_index=write_batch_index,
                phase=phase,
                max_retries=config.bq_write_max_retries,
                retry_base_seconds=config.bq_write_retry_base_seconds,
            ):
                stats.committed_batches += 1
            else:
                stats.skipped_batches += 1

    def flush_gemini_queue(max_sentences: int) -> None:
        fallback_sentences = list(pending_fallback)[:max_sentences]
        if not fallback_sentences:
            return
        grouped_annotations = router.annotate_gemini_many(fallback_sentences)
        ready: list[tuple[SentenceRecord, list[dict]]] = []
        for sentence in fallback_sentences:
            records_for_sentence = pending_fallback.pop(sentence)
            annotations = grouped_annotations.get(sentence, [])
            if progress is not None:
                progress.update(len(records_for_sentence))
            if not annotations:
                stats.unresolved_sentences += len(records_for_sentence)
                continue
            gemini_cache[sentence] = annotations
            ready.extend((record, annotations) for record in records_for_sentence)
        persist(ready, phase="gemini")

    for record_batch in _chunks(records, config.bq_write_batch_size):
        local_annotations = router.annotate_local_many(
            [record.sentence_text for record in record_batch]
        )
        local_ready: list[tuple[SentenceRecord, list[dict]]] = []
        cached_gemini_ready: list[tuple[SentenceRecord, list[dict]]] = []
        completed_locally = 0

        for record, annotations in zip(record_batch, local_annotations):
            if annotations is not None:
                completed_locally += 1
                if annotations:
                    local_ready.append((record, annotations))
                else:
                    stats.unresolved_sentences += 1
                continue

            if record.sentence_text in gemini_cache:
                completed_locally += 1
                cached_gemini_ready.append((record, gemini_cache[record.sentence_text]))
            else:
                pending_fallback[record.sentence_text].append(record)

        persist(local_ready, phase="local")
        persist(cached_gemini_ready, phase="gemini")
        if progress is not None and completed_locally:
            progress.update(completed_locally)
        while len(pending_fallback) >= config.gemini_batch_size:
            flush_gemini_queue(config.gemini_batch_size)

    while pending_fallback:
        flush_gemini_queue(config.gemini_batch_size)

    logger.info(
        "BigQuery checkpoint summary: %d committed batches, %d skipped batches, "
        "%d unresolved sentences",
        stats.committed_batches,
        stats.skipped_batches,
        stats.unresolved_sentences,
    )
    return sorted(
        output,
        key=lambda row: record_order.get(str(row["sentence_id"]), len(record_order)),
    )


def run(
    limit: int = _DEFAULT_LIMIT,
    input_jsonl: Path | None = None,
    output_jsonl: Path | None = None,
    write_bq: bool = True,
    dag_run_id: str = _DEFAULT_DAG_RUN_ID,
    reprocess: bool = False,
    router: ConfidenceRouter | None = None,
) -> list[dict]:
    records = (
        rows_from_jsonl(input_jsonl)
        if input_jsonl
        else fetch_unprocessed_sentences(limit, reprocess=reprocess)
    )
    if limit and input_jsonl:
        records = records[:limit]

    logger.info("Running NLP inference for %d sentences", len(records))
    router = router or ConfidenceRouter()
    with progress_bar(total=len(records), desc="NLP inference", unit="sentence") as progress:
        if write_bq:
            result_rows = _run_and_write_bq_batches(
                records,
                router,
                dag_run_id,
                load_nlp_config(),
                progress=progress,
            )
        else:
            result_rows = build_result_rows(records, router, dag_run_id=dag_run_id)
            progress.update(len(records))
    logger.info("NLP inference produced %d result rows", len(result_rows))

    if output_jsonl:
        write_jsonl(output_jsonl, result_rows)
        logger.info("Wrote NLP results to %s", output_jsonl)

    return result_rows


def debug_local_confidence(
    limit: int = _DEFAULT_LIMIT,
    input_jsonl: Path | None = None,
    output_jsonl: Path | None = None,
    reprocess: bool = False,
    router: ConfidenceRouter | None = None,
) -> list[dict]:
    records = (
        rows_from_jsonl(input_jsonl)
        if input_jsonl
        else fetch_unprocessed_sentences(limit, reprocess=reprocess)
    )
    if limit and input_jsonl:
        records = records[:limit]

    logger.info("Debugging local model confidence for %d sentences", len(records))
    rows = build_local_debug_rows(
        progress_bar(records, desc="NLP confidence debug", unit="sentence"),
        router or ConfidenceRouter(),
    )
    log_debug_summary(rows)

    if output_jsonl:
        write_jsonl(output_jsonl, rows)
        logger.info("Wrote local confidence debug rows to %s", output_jsonl)

    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local NLP inference pipeline")
    parser.add_argument("--limit", type=int, default=_DEFAULT_LIMIT)
    parser.add_argument("--input-jsonl", type=Path)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--no-write-bq", action="store_true")
    parser.add_argument("--debug-local-confidence", action="store_true")
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Allow selecting already processed sentences and upsert by result_id.",
    )
    parser.add_argument("--dag-run-id", default=os.environ.get("AIRFLOW_CTX_DAG_RUN_ID", _DEFAULT_DAG_RUN_ID))
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    args = _parse_args()
    if args.debug_local_confidence:
        debug_local_confidence(
            limit=args.limit,
            input_jsonl=args.input_jsonl,
            output_jsonl=args.output_jsonl,
            reprocess=args.reprocess,
        )
        return

    run(
        limit=args.limit,
        input_jsonl=args.input_jsonl,
        output_jsonl=args.output_jsonl,
        write_bq=not args.no_write_bq,
        dag_run_id=args.dag_run_id,
        reprocess=args.reprocess,
    )


if __name__ == "__main__":
    main()
