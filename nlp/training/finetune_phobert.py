from __future__ import annotations

# Google Colab: !pip install datasets underthesea
# Upload annotated_data.json to Google Drive before running.

import json

import numpy as np
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)
from underthesea import word_tokenize

_MODEL_NAME = "vinai/phobert-base"
_DATA_PATH = "/content/drive/MyDrive/thesis/annotated_data.json"
_OUTPUT_DIR = "/content/drive/MyDrive/thesis/models/phobert_sentiment"
_MAX_LEN = 256
_EPOCHS = 5
_BATCH_SIZE = 16
_LR = 2e-5

_LABELS = ["positive", "negative", "neutral"]
_LABEL2ID = {label: i for i, label in enumerate(_LABELS)}
_ID2LABEL = {i: label for label, i in _LABEL2ID.items()}


def _segment(text: str) -> str:
    return word_tokenize(text, format="text")


def _load_dataset(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        samples = json.load(f)
    records = [
        {
            "segment_text": s["segment_text"],
            "sentence": s["sentence"],
            "labels": _LABEL2ID[s["sentiment_label"]],
        }
        for s in samples
        if s["aspect_label"] != "NONE" and s["sentiment_label"] in _LABEL2ID
    ]
    return Dataset.from_list(records).train_test_split(test_size=0.1, seed=42)


def _tokenize(batch: dict, tokenizer) -> dict:
    return tokenizer(
        [_segment(seg) for seg in batch["segment_text"]],
        [_segment(sent) for sent in batch["sentence"]],
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )


def _compute_metrics(eval_pred) -> dict:
    from sklearn.metrics import f1_score  # pre-installed in Colab

    preds = np.argmax(eval_pred.predictions, axis=-1)
    return {"f1": f1_score(eval_pred.label_ids, preds, average="macro")}


def main() -> None:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    splits = _load_dataset(_DATA_PATH)
    tokenized = splits.map(
        lambda b: _tokenize(b, tokenizer),
        batched=True,
        remove_columns=["segment_text", "sentence"],
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        _MODEL_NAME,
        num_labels=len(_LABELS),
        id2label=_ID2LABEL,
        label2id=_LABEL2ID,
    )

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=_OUTPUT_DIR,
            num_train_epochs=_EPOCHS,
            per_device_train_batch_size=_BATCH_SIZE,
            per_device_eval_batch_size=_BATCH_SIZE,
            learning_rate=_LR,
            weight_decay=0.01,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            fp16=True,
            logging_steps=50,
            push_to_hub=False,
        ),
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=_compute_metrics,
    )

    trainer.train()
    trainer.save_model(_OUTPUT_DIR)
    tokenizer.save_pretrained(_OUTPUT_DIR)


if __name__ == "__main__":
    main()
