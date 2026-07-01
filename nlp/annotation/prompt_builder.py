from __future__ import annotations

import hashlib
import json

from nlp.annotation.prompt_config import FEW_SHOT_EXAMPLES, get_system_prompt


def annotation_input_id(sentence: str) -> str:
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()


def _with_input_id(item: dict) -> dict:
    return {
        "input_id": annotation_input_id(str(item["sentence"])),
        **item,
    }


class PromptBuilder:
    def build_annotation_prompt(self, sentences: list[str]) -> str:
        examples_json = json.dumps(
            [_with_input_id(item) for item in FEW_SHOT_EXAMPLES],
            ensure_ascii=False,
            indent=2,
        )
        sentences_json = json.dumps(
            [
                {"input_id": annotation_input_id(sentence), "sentence": sentence}
                for sentence in sentences
            ],
            ensure_ascii=False,
            indent=2,
        )
        
        system_prompt = get_system_prompt()
        
        return (
            f"{system_prompt}"
            f"{examples_json}\n\n"
            f"Danh sách câu cần gán nhãn:\n{sentences_json}"
        )
