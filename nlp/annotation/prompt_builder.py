from __future__ import annotations

import json

from nlp.annotation.prompt_config import FEW_SHOT_EXAMPLES, get_system_prompt


class PromptBuilder:
    def build_annotation_prompt(self, sentences: list[str]) -> str:
        examples_json = json.dumps(FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)
        sentences_json = json.dumps(sentences, ensure_ascii=False, indent=2)
        
        system_prompt = get_system_prompt()
        
        return (
            f"{system_prompt}"
            f"{examples_json}\n\n"
            f"Danh sách câu cần gán nhãn:\n{sentences_json}"
        )
