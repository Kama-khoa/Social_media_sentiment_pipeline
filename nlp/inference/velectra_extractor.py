from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForTokenClassification, AutoTokenizer
from underthesea import word_tokenize

_DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "velectra_aspect"


class VELECTRAExtractor:
    def __init__(self, model_dir: str | Path = _DEFAULT_MODEL_DIR) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
        self._model.eval()
        self._id2label = self._model.config.id2label
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

    def extract(self, sentence: str) -> list[dict]:
        sentence = sentence.strip()
        if not sentence:
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]

        raw_tokens = word_tokenize(sentence)
        tokens = []
        for t in raw_tokens:
            tokens.extend(str(t).split())

        if not tokens:
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": 1.0}]

        encoding = self._tokenizer(
            tokens,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        word_ids = encoding.word_ids(batch_index=0)
        inputs = {k: v.to(self._device) for k, v in encoding.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits[0]

        probs = F.softmax(logits, dim=-1)
        pred_ids = logits.argmax(dim=-1)

        word_labels: dict[int, tuple[str, float]] = {}
        for pos, wid in enumerate(word_ids):
            if wid is None or wid in word_labels:
                continue
            label = self._id2label[pred_ids[pos].item()]
            conf = probs[pos, pred_ids[pos]].item()
            word_labels[wid] = (label, conf)

        for i in range(len(tokens)):
            if i not in word_labels:
                word_labels[i] = ("O", 0.5)

        tag_seq = [word_labels[i][0] for i in range(len(tokens))]
        conf_seq = [word_labels[i][1] for i in range(len(tokens))]

        return self._decode_spans(tokens, tag_seq, conf_seq)

    def _decode_spans(
        self,
        tokens: list[str],
        tags: list[str],
        confs: list[float],
    ) -> list[dict]:
        spans: list[dict] = []
        span_tokens: list[str] = []
        span_confs: list[float] = []
        current_label: str | None = None

        for token, tag, conf in zip(tokens, tags, confs):
            if tag.startswith("B-"):
                if current_label is not None:
                    spans.append({
                        "aspect_label": current_label,
                        "segment_text": " ".join(span_tokens),
                        "confidence": min(span_confs),
                    })
                current_label = tag[2:]
                span_tokens = [token]
                span_confs = [conf]
            elif tag.startswith("I-") and current_label == tag[2:]:
                span_tokens.append(token)
                span_confs.append(conf)
            else:
                if current_label is not None:
                    spans.append({
                        "aspect_label": current_label,
                        "segment_text": " ".join(span_tokens),
                        "confidence": min(span_confs),
                    })
                current_label = None
                span_tokens = []
                span_confs = []

        if current_label is not None:
            spans.append({
                "aspect_label": current_label,
                "segment_text": " ".join(span_tokens),
                "confidence": min(span_confs),
            })

        if not spans:
            o_confs = [c for t, c in zip(tags, confs) if t == "O"]
            avg_o_conf = sum(o_confs) / max(len(o_confs), 1)
            return [{"aspect_label": "NONE", "segment_text": "", "confidence": avg_o_conf}]

        return spans
