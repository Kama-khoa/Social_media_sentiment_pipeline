from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock

import pytest

import nlp.runner as runner_module
from nlp.config import NLPConfig
from nlp.runner import (
    SentenceRecord,
    _run_and_write_bq_batches,
    _build_merge_sql,
    build_local_debug_rows,
    build_result_rows,
    run,
    write_rows_to_bigquery,
    write_rows_to_bigquery_with_retry,
)


class _FakeRouter:
    def annotate_many(self, sentences: list[str]) -> list[list[dict]]:
        return [
            [
                {
                    "sentence": sentence,
                    "aspect_label": "Pin",
                    "segment_text": "pin",
                    "sentiment_label": "positive",
                    "source": "model",
                    "confidence": 0.91,
                },
                {
                    "sentence": sentence,
                    "aspect_label": "Camera",
                    "segment_text": "camera",
                    "sentiment_label": "negative",
                    "source": "gemini",
                },
            ]
            for sentence in sentences
        ]


def test_build_result_rows_maps_router_output_to_bq_schema() -> None:
    rows = build_result_rows(
        [
            SentenceRecord(
                sentence_id="s1",
                comment_id="c1",
                video_id="v1",
                sentence_text="pin tốt nhưng camera tệ",
            )
        ],
        router=_FakeRouter(),
        dag_run_id="test-run",
        processed_at="2026-05-30T00:00:00+00:00",
    )

    assert rows == [
        {
            "result_id": rows[0]["result_id"],
            "sentence_id": "s1",
            "comment_id": "c1",
            "video_id": "v1",
            "aspect_label": "Pin",
            "segment_text": "pin",
            "sentiment_label": "positive",
            "confidence_score": 0.91,
            "inference_model": "velectra_aspect+phobert_sentiment",
            "dag_run_id": "test-run",
            "processed_at": "2026-05-30T00:00:00+00:00",
        },
        {
            "result_id": rows[1]["result_id"],
            "sentence_id": "s1",
            "comment_id": "c1",
            "video_id": "v1",
            "aspect_label": "Camera",
            "segment_text": "camera",
            "sentiment_label": "negative",
            "confidence_score": 1.0,
            "inference_model": "gemini_fallback",
            "dag_run_id": "test-run",
            "processed_at": "2026-05-30T00:00:00+00:00",
        },
    ]
    assert rows[0]["result_id"] != rows[1]["result_id"]


def test_build_result_rows_skips_records_without_annotations() -> None:
    class MissingAnnotationRouter:
        def annotate_many(self, sentences: list[str]) -> list[list[dict]]:
            return [[], [{
                "sentence": sentences[1],
                "aspect_label": "Pin",
                "segment_text": "pin",
                "sentiment_label": "positive",
                "source": "model",
                "confidence": 0.91,
            }]]

    rows = build_result_rows(
        [
            SentenceRecord("s1", "c1", "v1", "missing"),
            SentenceRecord("s2", "c2", "v2", "pin tot"),
        ],
        router=MissingAnnotationRouter(),
        processed_at="2026-05-30T00:00:00+00:00",
    )

    assert [row["sentence_id"] for row in rows] == ["s2"]


class _DebugRouter:
    def diagnose_local(self, sentence: str) -> list[dict]:
        return [
            {
                "aspect_label": "Pin",
                "segment_text": "pin",
                "sentiment_label": "positive",
                "ner_confidence": 0.93,
                "sentiment_confidence": 0.62,
                "confidence": 0.62,
                "would_fallback": True,
                "fallback_reason": "sentiment_confidence_below_threshold",
            }
        ]


def test_build_local_debug_rows_maps_router_diagnostics() -> None:
    rows = build_local_debug_rows(
        [
            SentenceRecord(
                sentence_id="s1",
                comment_id="c1",
                video_id="v1",
                sentence_text="pin ổn",
            )
        ],
        router=_DebugRouter(),
    )

    assert rows == [
        {
            "sentence_id": "s1",
            "comment_id": "c1",
            "video_id": "v1",
            "sentence_text": "pin ổn",
            "aspect_label": "Pin",
            "segment_text": "pin",
            "sentiment_label": "positive",
            "ner_confidence": 0.93,
            "sentiment_confidence": 0.62,
            "confidence": 0.62,
            "would_fallback": True,
            "fallback_reason": "sentiment_confidence_below_threshold",
        }
    ]


def test_build_merge_sql_upserts_by_result_id() -> None:
    sql = _build_merge_sql("project.dataset.raw_sentiment_results", "project.dataset.stage")

    assert "MERGE `project.dataset.raw_sentiment_results` T" in sql
    assert "USING `project.dataset.stage` S" in sql
    assert "ON T.result_id = S.result_id" in sql
    assert "WHEN MATCHED THEN UPDATE SET" in sql
    assert "confidence_score = S.confidence_score" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_run_and_write_bq_batches_checkpoints_local_and_queues_unique_gemini(
    monkeypatch,
) -> None:
    class BatchRouter:
        def __init__(self) -> None:
            self.gemini_calls: list[list[str]] = []

        def annotate_local_many(self, sentences: list[str]) -> list[list[dict] | None]:
            return [
                None if sentence.startswith("low") else [{
                    "sentence": sentence,
                    "aspect_label": "Pin",
                    "segment_text": "pin",
                    "sentiment_label": "positive",
                    "source": "model",
                    "confidence": 0.91,
                }]
                for sentence in sentences
            ]

        def annotate_gemini_many(self, sentences: list[str]) -> dict[str, list[dict]]:
            self.gemini_calls.append(sentences)
            return {
                sentence: [{
                    "sentence": sentence,
                    "aspect_label": "Pin",
                    "segment_text": "pin",
                    "sentiment_label": "negative",
                    "source": "gemini",
                }]
                for sentence in sentences
            }

    writes: list[tuple[str, list[str]]] = []

    def fake_write(rows: list[dict], **kwargs) -> bool:
        writes.append((kwargs["phase"], [row["sentence_id"] for row in rows]))
        return True

    monkeypatch.setattr(runner_module, "write_rows_to_bigquery_with_retry", fake_write)
    router = BatchRouter()
    progress = MagicMock()
    rows = _run_and_write_bq_batches(
        [
            SentenceRecord("s1", "c1", "v1", "accepted"),
            SentenceRecord("s2", "c2", "v2", "low one"),
            SentenceRecord("s3", "c3", "v3", "low two"),
            SentenceRecord("s4", "c4", "v4", "low one"),
        ],
        router,
        "test-run",
        NLPConfig(bq_write_batch_size=2, gemini_batch_size=2),
        progress=progress,
    )

    assert router.gemini_calls == [["low one", "low two"]]
    assert writes == [
        ("local", ["s1"]),
        ("gemini", ["s2", "s4"]),
        ("gemini", ["s3"]),
    ]
    assert sum(call.args[0] for call in progress.update.call_args_list) == 4
    assert [row["sentence_id"] for row in rows] == ["s1", "s2", "s3", "s4"]


def test_write_rows_to_bigquery_with_retry_uses_exponential_delays(monkeypatch) -> None:
    attempts = 0
    delays: list[float] = []

    def flaky_write(rows: list[dict]) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary")

    monkeypatch.setattr(runner_module, "write_rows_to_bigquery", flaky_write)
    monkeypatch.setattr(runner_module.time, "sleep", delays.append)

    assert write_rows_to_bigquery_with_retry(
        [{"sentence_id": "s1"}],
        dag_run_id="test-run",
        batch_index=1,
        phase="local",
        max_retries=2,
        retry_base_seconds=2,
    )
    assert attempts == 3
    assert delays == [2, 4]


def test_write_rows_to_bigquery_with_retry_logs_payload_after_final_failure(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        runner_module,
        "write_rows_to_bigquery",
        lambda rows: (_ for _ in ()).throw(RuntimeError("permanent")),
    )
    monkeypatch.setattr(runner_module.time, "sleep", lambda delay: None)
    monkeypatch.setattr(runner_module, "_FAILED_BATCH_LOG_DIR", tmp_path)
    rows = [{"sentence_id": "s1", "result_id": "r1"}]

    assert not write_rows_to_bigquery_with_retry(
        rows,
        dag_run_id="scheduled__2026-06-01T00:00:00+00:00",
        batch_index=3,
        phase="gemini",
        max_retries=2,
        retry_base_seconds=2,
    )

    log_files = list(tmp_path.glob("*.jsonl"))
    assert len(log_files) == 1
    payload = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert payload["batch_index"] == 3
    assert payload["phase"] == "gemini"
    assert payload["sentence_ids"] == ["s1"]
    assert payload["attempts"] == 3
    assert payload["rows"] == rows


def test_write_rows_to_bigquery_deletes_staging_table_when_load_fails(
    monkeypatch,
) -> None:
    deleted_tables: list[str] = []

    class FakeClient:
        def load_table_from_json(self, rows, staging_table, job_config):
            raise RuntimeError("load failed")

        def delete_table(self, staging_table, not_found_ok):
            deleted_tables.append(staging_table)

    fake_bigquery = types.SimpleNamespace(
        Client=lambda project: FakeClient(),
        LoadJobConfig=lambda **kwargs: kwargs,
        WriteDisposition=types.SimpleNamespace(WRITE_TRUNCATE="truncate"),
        SchemaField=lambda *args, **kwargs: (args, kwargs),
    )
    fake_cloud = types.ModuleType("google.cloud")
    fake_cloud.bigquery = fake_bigquery
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setenv("GCP_PROJECT_ID", "project")
    monkeypatch.setenv("BQ_DATASET", "dataset")

    with pytest.raises(RuntimeError, match="load failed"):
        write_rows_to_bigquery([{"sentence_id": "s1"}])

    assert len(deleted_tables) == 1


def test_run_and_write_bq_batches_continues_after_skipped_batch(monkeypatch) -> None:
    class LocalRouter:
        def annotate_local_many(self, sentences: list[str]) -> list[list[dict]]:
            return [[{
                "sentence": sentence,
                "aspect_label": "Pin",
                "segment_text": "pin",
                "sentiment_label": "positive",
                "source": "model",
                "confidence": 0.91,
            }] for sentence in sentences]

        def annotate_gemini_many(self, sentences: list[str]) -> dict[str, list[dict]]:
            raise AssertionError("Gemini should not be called")

    writes: list[str] = []

    def fake_write(rows: list[dict], **kwargs) -> bool:
        writes.append(rows[0]["sentence_id"])
        return len(writes) > 1

    monkeypatch.setattr(runner_module, "write_rows_to_bigquery_with_retry", fake_write)
    rows = _run_and_write_bq_batches(
        [
            SentenceRecord("s1", "c1", "v1", "first"),
            SentenceRecord("s2", "c2", "v2", "second"),
        ],
        LocalRouter(),
        "test-run",
        NLPConfig(bq_write_batch_size=1),
    )

    assert writes == ["s1", "s2"]
    assert [row["sentence_id"] for row in rows] == ["s1", "s2"]


def test_run_without_bq_keeps_single_pass_router_behavior(monkeypatch) -> None:
    monkeypatch.setattr(
        runner_module,
        "fetch_unprocessed_sentences",
        lambda limit, reprocess=False: [SentenceRecord("s1", "c1", "v1", "accepted")],
    )
    monkeypatch.setattr(
        runner_module,
        "_run_and_write_bq_batches",
        lambda *args, **kwargs: pytest.fail("Production checkpoint path should not run"),
    )

    rows = run(limit=1, write_bq=False, router=_FakeRouter())

    assert [row["sentence_id"] for row in rows] == ["s1", "s1"]


def test_fetch_unprocessed_sentences_omits_limit_when_limit_is_zero(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeQueryResult:
        def result(self):
            return []

    class FakeClient:
        def __init__(self, project):
            captured["project"] = project

        def query(self, sql, job_config):
            captured["sql"] = sql
            captured["job_config"] = job_config
            return FakeQueryResult()

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        QueryJobConfig=lambda **kwargs: kwargs,
        ScalarQueryParameter=lambda *args: args,
    )
    fake_cloud = types.ModuleType("google.cloud")
    fake_cloud.bigquery = fake_bigquery
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setenv("GCP_PROJECT_ID", "project")
    monkeypatch.setenv("BQ_DATASET", "dataset")

    assert runner_module.fetch_unprocessed_sentences(limit=0) == []
    assert "LIMIT @limit" not in captured["sql"]
    assert captured["job_config"]["query_parameters"] == []
