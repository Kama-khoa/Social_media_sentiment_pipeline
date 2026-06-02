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
    resolver._candidates = lambda limit: [
        {"candidate_id": f"candidate-{index}", "source_type": "video", "source_id": f"video-{index}"}
        for index in range(5)
    ]
    batch_sizes = []

    def ask_batch(batch, catalog):
        batch_sizes.append(len(batch))
        return {
            item["candidate_id"]: {"product_ids": ["iphone-16"]}
            for item in batch
        }

    resolver._ask_gemini_batch = ask_batch
    resolver._apply_result = lambda candidate, result, valid_ids: True

    result = resolver.run(limit=5, batch_size=2)

    assert batch_sizes == [2, 2, 1]
    assert result == {"processed": 5, "resolved": 5, "pending": 0}
