from unittest.mock import MagicMock

import pytest

from nlp.product_target_resolver import ProductTargetResolver, _extract_json


def test_extract_json_accepts_plain_object():
    assert _extract_json('{"product_ids": ["iphone-16"]}') == {"product_ids": ["iphone-16"]}


def test_extract_json_accepts_markdown_fence():
    assert _extract_json('```json\n{"targets": []}\n```') == {"targets": []}


def test_extract_json_rejects_invalid_payload():
    with pytest.raises(ValueError):
        _extract_json("not-json")


def test_ask_gemini_batch_maps_results_by_candidate_id():
    resolver = object.__new__(ProductTargetResolver)
    resolver.gemini = MagicMock()
    resolver.gemini.generate.return_value = (
        '[{"candidate_id":"candidate-1","product_ids":["iphone-16"],"targets":[]}]'
    )

    result = resolver._ask_gemini_batch(
        [{"candidate_id": "candidate-1", "source_type": "video", "candidate_text": "Review iPhone 16"}],
        [{"product_id": "iphone-16", "product_name": "iPhone 16", "aliases": ["iphone 16"]}],
    )

    assert result["candidate-1"]["product_ids"] == ["iphone-16"]
    resolver.gemini.generate.assert_called_once()


def test_run_sends_candidates_in_batches():
    resolver = object.__new__(ProductTargetResolver)
    resolver._catalog = lambda: [{"product_id": "iphone-16"}]
    resolver._active_aliases = lambda: set()
    resolver.auto_approve_threshold = 0.85
    resolver.recheck_batch_size = 50
    resolver._candidates = lambda limit: [
        {"candidate_id": f"candidate-{index}", "source_type": "video", "source_id": f"video-{index}"}
        for index in range(5)
    ]
    batch_sizes = []

    def ask_batch(batch, catalog):
        batch_sizes.append(len(batch))
        return {
            item["candidate_id"]: {"product_ids": ["iphone-16"], "confidence": 0.85}
            for item in batch
        }

    resolver._ask_gemini_batch = ask_batch
    resolver._ask_gemini_recheck_batch = MagicMock()
    resolver._apply_result = lambda candidate, result, valid_ids, method, alias_index: True

    result = resolver.run(limit=5, batch_size=2)

    assert batch_sizes == [2, 2, 1]
    assert result == {"processed": 5, "resolved": 5, "pending": 0}
    resolver._ask_gemini_recheck_batch.assert_not_called()


def test_low_confidence_candidate_is_rechecked_before_pending():
    resolver = object.__new__(ProductTargetResolver)
    resolver._catalog = lambda: [{"product_id": "iphone-16"}]
    resolver._active_aliases = lambda: set()
    resolver.auto_approve_threshold = 0.85
    resolver.recheck_batch_size = 50
    resolver._candidates = lambda limit: [
        {"candidate_id": "candidate-1", "source_type": "video", "source_id": "video-1", "candidate_text": "ip16"}
    ]
    resolver._ask_gemini_batch = lambda batch, catalog: {
        "candidate-1": {"product_ids": ["iphone-16"], "confidence": 0.84, "reason": "likely but uncertain"}
    }
    resolver._ask_gemini_recheck_batch = MagicMock(return_value={
        "candidate-1": {"product_ids": ["iphone-16"], "confidence": 0.85, "reason": "confirmed"}
    })
    applied = []
    resolver._apply_result = lambda candidate, result, valid_ids, method, alias_index: applied.append(method) or True
    resolver._audit = MagicMock()

    result = resolver.run(limit=1, batch_size=10)

    assert result == {"processed": 1, "resolved": 1, "pending": 0}
    assert applied == ["llm_batch_recheck"]
    resolver._audit.assert_not_called()


def test_candidate_stays_pending_after_low_confidence_recheck():
    resolver = object.__new__(ProductTargetResolver)
    resolver.gemini = MagicMock(last_model="gemini-test")
    resolver._catalog = lambda: [{"product_id": "iphone-16"}]
    resolver._active_aliases = lambda: set()
    resolver.auto_approve_threshold = 0.85
    resolver.recheck_batch_size = 50
    resolver._candidates = lambda limit: [
        {"candidate_id": "candidate-1", "source_type": "video", "source_id": "video-1", "candidate_text": "cai thu 2"}
    ]
    resolver._ask_gemini_batch = lambda batch, catalog: {
        "candidate-1": {"product_ids": ["iphone-16"], "confidence": 0.84, "reason": "uncertain"}
    }
    resolver._ask_gemini_recheck_batch = lambda batch, catalog: {
        "candidate-1": {"product_ids": ["iphone-16"], "confidence": 0.80, "reason": "still ambiguous"}
    }
    resolver._audit = MagicMock()

    result = resolver.run(limit=1, batch_size=10)

    assert result == {"processed": 1, "resolved": 0, "pending": 1}
    resolver._audit.assert_called_once()
    assert resolver._audit.call_args.args[1] == "pending"
    assert resolver._audit.call_args.kwargs["method"] == "llm_batch_recheck"


def test_sentence_requires_target_confidence_and_sentiment():
    resolver = object.__new__(ProductTargetResolver)
    resolver.auto_approve_threshold = 0.85
    candidate = {"source_type": "sentence"}
    valid_ids = {"iphone-16"}

    assert resolver._result_is_auto_approvable(
        candidate,
        {
            "confidence": 0.91,
            "targets": [{"product_id": "iphone-16", "sentiment_label": "POSITIVE", "confidence": 0.85}],
        },
        valid_ids,
    )
    assert not resolver._result_is_auto_approvable(
        candidate,
        {
            "confidence": 0.91,
            "targets": [{"product_id": "iphone-16", "sentiment_label": "POSITIVE", "confidence": 0.84}],
        },
        valid_ids,
    )
    assert not resolver._result_is_auto_approvable(
        candidate,
        {"confidence": 0.91, "targets": [{"product_id": "iphone-16", "confidence": 0.91}]},
        valid_ids,
    )


def test_alias_is_created_only_at_alias_threshold():
    resolver = object.__new__(ProductTargetResolver)
    resolver.auto_alias_threshold = 0.90
    resolver._table = lambda name: f"`project.dataset.{name}`"
    resolver.client = MagicMock()
    resolver.client.query.return_value.result.return_value = None

    alias_index = set()
    resolver._maybe_create_alias(
        {"confidence": 0.89, "alias_suggestion": "ip16"},
        ["iphone-16"],
        alias_index,
    )
    resolver._maybe_create_alias(
        {"confidence": 0.90, "alias_suggestion": "ip16"},
        ["iphone-16"],
        alias_index,
    )
    resolver._maybe_create_alias(
        {"confidence": 0.99, "alias_suggestion": "con nay"},
        ["iphone-16"],
        alias_index,
    )

    assert resolver.client.query.call_count == 1
    assert "ip16" in alias_index
