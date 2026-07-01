from __future__ import annotations

from nlp.annotation.gemini_annotator import GeminiAnnotator
from nlp.annotation.prompt_builder import annotation_input_id


def test_normalize_item_sentence_restores_original_text_from_input_id() -> None:
    annotator = object.__new__(GeminiAnnotator)
    original = "@ngango9888  camera của sony nhưng tinh chỉ là app"

    normalized = annotator._normalize_item_sentence(
        {
            "input_id": annotation_input_id(original),
            "sentence": "@ngango9888 camera của sony",
        },
        [original],
    )

    assert normalized is not None
    assert normalized["sentence"] == original


def test_annotate_all_retries_only_missing_sentences() -> None:
    annotator = object.__new__(GeminiAnnotator)
    annotator._batch_size = 50
    calls: list[list[str]] = []

    def annotate_batch(sentences: list[str]) -> list[dict]:
        calls.append(sentences)
        returned_sentences = sentences[:1] if len(calls) == 1 else sentences
        return [{"sentence": sentence} for sentence in returned_sentences]

    annotator._annotate_batch = annotate_batch

    results = annotator.annotate_all(["first", "second", "third"])

    assert calls == [["first", "second", "third"], ["second", "third"]]
    assert [item["sentence"] for item in results] == ["first", "second", "third"]
