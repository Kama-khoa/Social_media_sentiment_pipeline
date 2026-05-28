from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from pyvi import ViTokenizer

_DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "phobert_sentiment"


class PhoBERTClassifier:
    def __init__(self, model_dir: str | Path = _DEFAULT_MODEL_DIR) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        self._model.eval()
        self._id2label = self._model.config.id2label
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

    def classify(self, comment_text: str, aspect_label: str) -> tuple[str, float]:
        aspect_segmented = ViTokenizer.tokenize(aspect_label) if aspect_label.strip() else ""
        sent_segmented = ViTokenizer.tokenize(comment_text)

        inputs = self._tokenizer(
            aspect_segmented,
            sent_segmented,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits[0]

        probs = F.softmax(logits, dim=-1)
        pred_id = logits.argmax().item()

        return self._id2label[pred_id], probs[pred_id].item()
