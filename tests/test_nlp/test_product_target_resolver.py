import pytest

from nlp.product_target_resolver import _extract_json


def test_extract_json_accepts_plain_object():
    assert _extract_json('{"product_ids": ["iphone-16"]}') == {"product_ids": ["iphone-16"]}


def test_extract_json_accepts_markdown_fence():
    assert _extract_json('```json\n{"targets": []}\n```') == {"targets": []}


def test_extract_json_rejects_invalid_payload():
    with pytest.raises(ValueError):
        _extract_json("not-json")
