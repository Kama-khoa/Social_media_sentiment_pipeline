from __future__ import annotations

from nlp.runner import (
    SentenceRecord,
    _build_merge_sql,
    build_local_debug_rows,
    build_result_rows,
)


class _FakeRouter:
    def annotate(self, sentence: str) -> list[dict]:
        return [
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
