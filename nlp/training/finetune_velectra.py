from __future__ import annotations

# Google Colab: !pip install datasets seqeval underthesea
# Upload annotated_data.json to Google Drive before running.

import json

import numpy as np
from datasets import Dataset
from seqeval.metrics import f1_score
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)
from underthesea import word_tokenize

_MODEL_NAME = "FPTAI/velectra-base-discriminator-cased"
_DATA_PATH = "/content/drive/MyDrive/thesis/annotated_data.json"
_OUTPUT_DIR = "/content/drive/MyDrive/thesis/models/velectra_aspect"
_MAX_LEN = 256
_EPOCHS = 5
_BATCH_SIZE = 16
_LR = 2e-5

_ASPECT_LABELS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]
_LABEL_LIST = ["O"] + [f"{p}-{a}" for a in _ASPECT_LABELS for p in ("B", "I")]
_LABEL2ID = {label: i for i, label in enumerate(_LABEL_LIST)}
_ID2LABEL = {i: label for label, i in _LABEL2ID.items()}


def _load_dataset(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        samples = json.load(f)
    records = [
        {"tokens": word_tokenize(s["sentence"]), "labels": s["bio_tags"]}
        for s in samples
        if len(word_tokenize(s["sentence"])) == len(s["bio_tags"])
    ]
    return Dataset.from_list(records).train_test_split(test_size=0.1, seed=42)


def _tokenize_and_align(batch: dict, tokenizer) -> dict:
    tokenized = tokenizer(
        batch["tokens"],
        is_split_into_words=True,
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )
    aligned = []
    for i, label_seq in enumerate(batch["labels"]):
        word_ids = tokenized.word_ids(batch_index=i)
        prev = None
        ids = []
        for wid in word_ids:
            if wid is None:
                ids.append(-100)
            elif wid != prev:
                ids.append(_LABEL2ID.get(label_seq[wid], 0))
            else:
                ids.append(-100)
            prev = wid
        aligned.append(ids)
    tokenized["labels"] = aligned
    return tokenized


def _compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    true = [[_LABEL_LIST[l] for l in row if l != -100] for row in labels]
    pred = [
        [_LABEL_LIST[p] for p, l in zip(p_row, l_row) if l != -100]
        for p_row, l_row in zip(preds, labels)
    ]
    return {"f1": f1_score(true, pred)}


def main() -> None:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    splits = _load_dataset(_DATA_PATH)
    tokenized = splits.map(
        lambda b: _tokenize_and_align(b, tokenizer),
        batched=True,
        remove_columns=["tokens", "labels"],
    )

    model = AutoModelForTokenClassification.from_pretrained(
        _MODEL_NAME,
        num_labels=len(_LABEL_LIST),
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
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=_compute_metrics,
    )

    trainer.train()
    trainer.save_model(_OUTPUT_DIR)
    tokenizer.save_pretrained(_OUTPUT_DIR)


if __name__ == "__main__":
    main()
