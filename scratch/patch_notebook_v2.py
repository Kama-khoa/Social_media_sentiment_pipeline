import json
import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    root = Path(__file__).parent.parent
    p = root / "nlp" / "training" / "Colab_Finetuning_Template.ipynb"
    
    if not p.exists():
        print(f"[LỖI] Không tìm thấy file template tại: {p}")
        return
        
    with open(p, 'r', encoding='utf-8') as f:
        d = json.load(f)

    # Khai báo index chính xác của các cell trong notebook
    install_cell_idx = 0
    load_data_cell_idx = 2
    phobert_setup_cell_idx = 4
    phobert_train_cell_idx = 5
    ner_setup_cell_idx = 7
    ner_train_cell_idx = 8

    # 1. Pip install cell
    d['cells'][install_cell_idx]['source'] = [
        "!pip install transformers datasets seqeval evaluate accelerate scikit-learn -q\n",
        "!pip install underthesea pyvi -q"
    ]

    # 2. Load data cell
    load_data_source = """from datasets import load_dataset

# 1. PhoBERT Sentiment Dataset (standard v2/v3 aspect-based)
phobert_sent_files = {
    "train": "/content/drive/MyDrive/dataset_hf/sentiment/phobert/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/sentiment/phobert/val.jsonl"
}
phobert_sent_raw = load_dataset("json", data_files=phobert_sent_files)

# 2. NER Datasets (V3 versions)
# vELECTRA/XLM-R Syllable none25
velectra_none25_files = {
    "train": "/content/drive/MyDrive/dataset_hf/ner/v3_none25/velectra/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/ner/v3_none25/velectra/val.jsonl"
}
ner_syllable_none25_raw = load_dataset("json", data_files=velectra_none25_files)

# vELECTRA Syllable none30 (for comparison)
velectra_none30_files = {
    "train": "/content/drive/MyDrive/dataset_hf/ner/v3_none30/velectra/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/ner/v3_none30/velectra/val.jsonl"
}
ner_syllable_none30_raw = load_dataset("json", data_files=velectra_none30_files)

# PhoBERT Word-segmented none25
phobert_ner_none25_files = {
    "train": "/content/drive/MyDrive/dataset_hf/ner/v3_none25/phobert/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/ner/v3_none25/phobert/val.jsonl"
}
ner_word_none25_raw = load_dataset("json", data_files=phobert_ner_none25_files)

print("PhoBERT Sentiment Dataset:", phobert_sent_raw)
print("Syllable none25 NER Dataset:", ner_syllable_none25_raw)
print("Syllable none30 NER Dataset:", ner_syllable_none30_raw)
print("Word-segmented none25 NER Dataset:", ner_word_none25_raw)"""
    d['cells'][load_data_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in load_data_source.splitlines()]

    # 3. PhoBERT Sentiment Setup cell
    phobert_setup_source = """import numpy as np
import csv
import torch
import torch.nn.functional as F
from transformers import (
    AutoModelForSequenceClassification, AutoTokenizer,
    DataCollatorWithPadding, Trainer, TrainingArguments, EarlyStoppingCallback
)
from pyvi import ViTokenizer

# --- CONFIGURATION FOR CURRENT RUN ---
LABEL_SMOOTHING_FACTOR = 0.05  # Tune: 0.03, 0.05, 0.08
RANDOM_SEED = 42                # Tune: 42, 3407, 2025
# -------------------------------------

model_checkpoint_phobert = "vinai/phobert-large"
tokenizer_phobert = AutoTokenizer.from_pretrained(model_checkpoint_phobert)

_MAX_LEN = 256
SENTIMENT_LABELS = ["negative", "neutral", "positive"]
SENTIMENT_LABEL2ID = {label: i for i, label in enumerate(SENTIMENT_LABELS)}
SENTIMENT_ID2LABEL = {i: label for label, i in SENTIMENT_LABEL2ID.items()}

def prepare_phobert_dataset(batch):
    # Word segmentation với pyvi cho cả text và aspect
    sentences = [ViTokenizer.tokenize(str(text)) for text in batch["text"]]
    aspects = [ViTokenizer.tokenize(str(a)) for a in batch["aspect"]]

    tokenized = tokenizer_phobert(
        aspects,
        sentences,
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )
    tokenized["labels"] = [SENTIMENT_LABEL2ID[str(lbl).strip().lower()] for lbl in batch["label"]]
    return tokenized

phobert_dataset = phobert_sent_raw.map(
    prepare_phobert_dataset,
    batched=True,
    remove_columns=phobert_sent_raw["train"].column_names
)

model_phobert = AutoModelForSequenceClassification.from_pretrained(
    model_checkpoint_phobert,
    num_labels=len(SENTIMENT_LABELS),
    id2label=SENTIMENT_ID2LABEL,
    label2id=SENTIMENT_LABEL2ID
)

def compute_metrics_phobert(eval_pred):
    from sklearn.metrics import f1_score, accuracy_score, classification_report
    preds = np.argmax(eval_pred.predictions, axis=-1)
    print("\\nPhoBERT Sentiment Report:")
    print(classification_report(eval_pred.label_ids, preds, target_names=SENTIMENT_LABELS, digits=4))
    return {
        "accuracy": accuracy_score(eval_pred.label_ids, preds),
        "f1": f1_score(eval_pred.label_ids, preds, average="macro")
    }

args_phobert = TrainingArguments(
    output_dir="/content/drive/MyDrive/models/phobert_sentiment",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=1e-5,
    weight_decay=0.01,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    label_smoothing_factor=LABEL_SMOOTHING_FACTOR,
    seed=RANDOM_SEED,
    data_seed=RANDOM_SEED,
    greater_is_better=True,
    save_total_limit=2,
    report_to="none"
)

trainer_phobert = Trainer(
    model=model_phobert,
    args=args_phobert,
    train_dataset=phobert_dataset["train"],
    eval_dataset=phobert_dataset["validation"],
    processing_class=tokenizer_phobert,
    data_collator=DataCollatorWithPadding(tokenizer_phobert),
    compute_metrics=compute_metrics_phobert,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.002)],
)

def export_phobert_errors(trainer, eval_dataset, raw_dataset, output_path):
    predictions = trainer.predict(eval_dataset)
    preds = np.argmax(predictions.predictions, axis=-1)
    labels = predictions.label_ids
    probs = F.softmax(torch.tensor(predictions.predictions), dim=-1).numpy()
    
    wrong_count = 0
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "aspect", "true_label", "pred_label", "confidence"])
        for idx, (pred, label) in enumerate(zip(preds, labels)):
            if pred != label:
                item = raw_dataset[idx]
                conf = probs[idx][pred]
                writer.writerow([
                    item["text"],
                    item["aspect"],
                    SENTIMENT_LABELS[label],
                    SENTIMENT_LABELS[pred],
                    f"{conf:.4f}"
                ])
                wrong_count += 1
    print(f"Exported {wrong_count} wrong predictions to {output_path}")"""
    d['cells'][phobert_setup_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in phobert_setup_source.splitlines()]

    # 4. PhoBERT Sentiment Train cell
    phobert_train_source = """# Chạy cell này khi muốn train PhoBERT Sentiment
trainer_phobert.train()
trainer_phobert.save_model("/content/drive/MyDrive/models/phobert_sentiment")

# Xuất lỗi dự đoán cho Error Analysis
error_csv_path = "/content/drive/MyDrive/experiments/error_analysis/phobert_wrong_predictions.csv"
export_phobert_errors(
    trainer_phobert, 
    phobert_dataset["validation"], 
    phobert_sent_raw["validation"], 
    error_csv_path
)"""
    d['cells'][phobert_train_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in phobert_train_source.splitlines()]

    # 5. NER Setup cell
    ner_setup_source = """import numpy as np
import json
from seqeval.metrics import f1_score, precision_score, recall_score, classification_report
from transformers import (
    AutoModelForTokenClassification, AutoTokenizer,
    DataCollatorForTokenClassification, EarlyStoppingCallback, Trainer, TrainingArguments
)

# --- CONFIGURATION FOR NER RUN ---
# Options: "FPTAI/velectra-base-discriminator-cased", "vinai/phobert-base-v2", "xlm-roberta-base"
MODEL_CHECKPOINT_NER = "FPTAI/velectra-base-discriminator-cased"
# Options: "none25", "none30"
NONE_RATIO_VERSION = "none25"
RANDOM_SEED_NER = 42
# ---------------------------------

tokenizer_velectra = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT_NER)
_MAX_LEN = 256

# Label configuration
ASPECT_LABELS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]
NER_LABEL_LIST = ["O"] + [f"{prefix}-{aspect}" for aspect in ASPECT_LABELS for prefix in ("B", "I")]
NER_LABEL2ID = {label: i for i, label in enumerate(NER_LABEL_LIST)}
NER_ID2LABEL = {i: label for label, i in NER_LABEL2ID.items()}

# Choose the correct dataset based on model checkpoint
if "phobert" in MODEL_CHECKPOINT_NER.lower():
    active_raw_dataset = ner_word_none25_raw
    print("Loading word-segmented dataset for PhoBERT NER...")
else:
    if NONE_RATIO_VERSION == "none30":
        active_raw_dataset = ner_syllable_none30_raw
        print("Loading syllable none30 dataset for NER...")
    else:
        active_raw_dataset = ner_syllable_none25_raw
        print("Loading syllable none25 dataset for NER...")

def tokenize_and_align_labels(batch):
    tokenized = tokenizer_velectra(
        batch["tokens"],
        truncation=True,
        is_split_into_words=True,
        max_length=_MAX_LEN,
        padding=False,
    )

    aligned_labels = []
    for i, label_seq in enumerate(batch["ner_tags"]):
        word_ids = tokenized.word_ids(batch_index=i)
        prev_word_id = None
        label_ids = []

        for word_id in word_ids:
            if word_id is None:
                label_ids.append(-100)
            elif word_id != prev_word_id:
                label_ids.append(NER_LABEL2ID.get(label_seq[word_id], NER_LABEL2ID["O"]))
            else:
                label_ids.append(-100)
            prev_word_id = word_id

        aligned_labels.append(label_ids)

    tokenized["labels"] = aligned_labels
    return tokenized

velectra_dataset = active_raw_dataset.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=active_raw_dataset["train"].column_names,
)

# Setup output directory
model_short_name = "velectra_aspect"
if "phobert" in MODEL_CHECKPOINT_NER.lower():
    model_short_name = "phobert_base_ner"
elif "roberta" in MODEL_CHECKPOINT_NER.lower():
    model_short_name = "xlm_roberta_ner"

output_model_dir = f"/content/drive/MyDrive/models/{model_short_name}"

model_velectra = AutoModelForTokenClassification.from_pretrained(
    MODEL_CHECKPOINT_NER,
    num_labels=len(NER_LABEL_LIST),
    id2label=NER_ID2LABEL,
    label2id=NER_LABEL2ID,
)

def compute_metrics_velectra(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    true_labels = []
    true_preds = []

    for pred_row, label_row in zip(preds, labels):
        row_labels = []
        row_preds = []
        for pred_id, label_id in zip(pred_row, label_row):
            if label_id != -100:
                row_labels.append(NER_ID2LABEL[label_id])
                row_preds.append(NER_ID2LABEL[pred_id])
        true_labels.append(row_labels)
        true_preds.append(row_preds)

    print("\\nNER Classification Report:")
    print(classification_report(true_labels, true_preds, digits=4))

    return {
        "precision": precision_score(true_labels, true_preds),
        "recall": recall_score(true_labels, true_preds),
        "f1": f1_score(true_labels, true_preds),
    }

args_velectra = TrainingArguments(
    output_dir=output_model_dir,
    num_train_epochs=10,
    learning_rate=1e-5,
    warmup_ratio=0.1,
    weight_decay=0.01,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    seed=RANDOM_SEED_NER,
    data_seed=RANDOM_SEED_NER,
    save_total_limit=2,
    report_to="none",
)

trainer_velectra = Trainer(
    model=model_velectra,
    args=args_velectra,
    train_dataset=velectra_dataset["train"],
    eval_dataset=velectra_dataset["validation"],
    processing_class=tokenizer_velectra,
    data_collator=DataCollatorForTokenClassification(tokenizer_velectra),
    compute_metrics=compute_metrics_velectra,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.002)],
)

def export_ner_errors(trainer, eval_dataset, raw_dataset, output_path):
    predictions = trainer.predict(eval_dataset)
    preds = np.argmax(predictions.predictions, axis=-1)
    labels = predictions.label_ids
    
    wrong_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, (pred_row, label_row) in enumerate(zip(preds, labels)):
            row_labels = []
            row_preds = []
            for pred_id, label_id in zip(pred_row, label_row):
                if label_id != -100:
                    row_labels.append(NER_ID2LABEL[label_id])
                    row_preds.append(NER_ID2LABEL[pred_id])
            
            if row_labels != row_preds:
                item = raw_dataset[idx]
                rec = {
                    "tokens": item["tokens"],
                    "true_labels": row_labels,
                    "pred_labels": row_preds,
                    "aspects": item.get("aspects", [])
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\\n")
                wrong_count += 1
    print(f"Exported {wrong_count} wrong predictions to {output_path}")"""
    d['cells'][ner_setup_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in ner_setup_source.splitlines()]

    # 6. NER Train cell
    ner_train_source = """# Chạy cell này khi muốn train NER
trainer_velectra.train()
trainer_velectra.save_model(output_model_dir)

# Xuất lỗi dự đoán cho Error Analysis
error_jsonl_path = "/content/drive/MyDrive/experiments/error_analysis/ner_wrong_predictions.jsonl"
export_ner_errors(
    trainer_velectra,
    velectra_dataset["validation"],
    active_raw_dataset["validation"],
    error_jsonl_path
)"""
    d['cells'][ner_train_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in ner_train_source.splitlines()]

    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1, ensure_ascii=False)

    print("Đã vá file Colab_Finetuning_Template.ipynb thành công!")

if __name__ == "__main__":
    main()
