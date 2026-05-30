import json
from pathlib import Path

def code_cell(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in src.strip("\n").split("\n")],
    }

def md_cell(src):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in src.strip("\n").split("\n")],
    }

# Chạy:
# python nlp/training/patch_notebook_v3.py
# hoặc:
# python patch_notebook_v3.py path/to/Colab_Finetuning_Template.ipynb

import sys

if len(sys.argv) > 1:
    notebook_path = Path(sys.argv[1])
else:
    notebook_path = Path(__file__).with_name("Colab_Finetuning_Template.ipynb")

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

install_src = """!pip install transformers datasets seqeval evaluate accelerate scikit-learn -q
!pip install underthesea pyvi -q"""

drive_src = """# Bước 1: Kết nối với Google Drive
from google.colab import drive
drive.mount('/content/drive')"""

load_src = """from datasets import load_dataset

# Dataset PhoBERT Sentiment: 1 record = 1 (comment, aspect, sentiment)
phobert_files = {
    "train": "/content/drive/MyDrive/dataset_hf/sentiment/phobert/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/sentiment/phobert/val.jsonl",
}
phobert_raw = load_dataset("json", data_files=phobert_files)

# Dataset vELECTRA NER: 1 record = 1 comment đã merge đầy đủ các aspect span
velectra_files = {
    "train": "/content/drive/MyDrive/dataset_hf/ner/velectra/train.jsonl",
    "validation": "/content/drive/MyDrive/dataset_hf/ner/velectra/val.jsonl",
}
velectra_raw = load_dataset("json", data_files=velectra_files)

print("PhoBERT Dataset:", phobert_raw)
print("vELECTRA Dataset:", velectra_raw)
print("PhoBERT columns:", phobert_raw["train"].column_names)
print("vELECTRA columns:", velectra_raw["train"].column_names)"""

phobert_src = r"""import numpy as np
from pyvi import ViTokenizer
from sklearn.metrics import f1_score, accuracy_score, classification_report
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)

# 1.1 Khởi tạo Tokenizer
model_checkpoint_phobert = "vinai/phobert-large"
tokenizer_phobert = AutoTokenizer.from_pretrained(model_checkpoint_phobert)

PHOBERT_MAX_LEN = 256
SENTIMENT_LABELS = ["negative", "neutral", "positive"]
SENTIMENT_LABEL2ID = {label: i for i, label in enumerate(SENTIMENT_LABELS)}
SENTIMENT_ID2LABEL = {i: label for label, i in SENTIMENT_LABEL2ID.items()}

# 1.2 Hàm Tokenize
def prepare_phobert_dataset(batch):
    # Word segmentation cho PhoBERT. Phải dùng cùng bước này khi inference.
    sentences = [ViTokenizer.tokenize(str(text)) for text in batch["text"]]
    aspects = [str(a) for a in batch["aspect"]]
    labels = [SENTIMENT_LABEL2ID[str(lbl).strip().lower()] for lbl in batch["label"]]

    # Pair sequence: aspect [SEP] comment
    tokenized = tokenizer_phobert(
        aspects,
        sentences,
        truncation=True,
        max_length=PHOBERT_MAX_LEN,
        padding=False,
    )
    tokenized["labels"] = labels
    return tokenized

phobert_dataset = phobert_raw.map(
    prepare_phobert_dataset,
    batched=True,
    remove_columns=phobert_raw["train"].column_names,
)

# 1.3 Setup Model & Trainer
model_phobert = AutoModelForSequenceClassification.from_pretrained(
    model_checkpoint_phobert,
    num_labels=len(SENTIMENT_LABELS),
    id2label=SENTIMENT_ID2LABEL,
    label2id=SENTIMENT_LABEL2ID,
)

def compute_metrics_phobert(eval_pred):
    preds = np.argmax(eval_pred.predictions, axis=-1)
    print("\nPhoBERT Sentiment Report:")
    print(classification_report(eval_pred.label_ids, preds, target_names=SENTIMENT_LABELS, digits=4))
    return {
        "accuracy": accuracy_score(eval_pred.label_ids, preds),
        "f1": f1_score(eval_pred.label_ids, preds, average="macro"),
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
    greater_is_better=True,
    save_total_limit=2,
    report_to="none",
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
)"""

train_phobert_src = """# Chạy cell này khi muốn train PhoBERT Sentiment
trainer_phobert.train()
trainer_phobert.save_model("/content/drive/MyDrive/models/phobert_sentiment")"""

velectra_src = r"""import numpy as np
from seqeval.metrics import f1_score, precision_score, recall_score, classification_report
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

# 2.1 Cấu hình Labels
ASPECT_LABELS = ["Camera", "Giá", "Hiệu năng", "Thiết kế", "Pin", "Màn hình"]
NER_LABEL_LIST = ["O"] + [f"{prefix}-{aspect}" for aspect in ASPECT_LABELS for prefix in ("B", "I")]
NER_LABEL2ID = {label: i for i, label in enumerate(NER_LABEL_LIST)}
NER_ID2LABEL = {i: label for label, i in NER_LABEL2ID.items()}

VELECTRA_MAX_LEN = 256
model_checkpoint_velectra = "FPTAI/velectra-base-discriminator-cased"
tokenizer_velectra = AutoTokenizer.from_pretrained(model_checkpoint_velectra, use_fast=True)

# 2.2 Align Tokens & Labels
def tokenize_and_align_labels(batch):
    tokenized = tokenizer_velectra(
        batch["tokens"],
        truncation=True,
        is_split_into_words=True,
        max_length=VELECTRA_MAX_LEN,
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
                # Không tính loss cho sub-token phụ để tránh lệch nhãn.
                label_ids.append(-100)
            prev_word_id = word_id

        aligned_labels.append(label_ids)

    tokenized["labels"] = aligned_labels
    return tokenized

velectra_dataset = velectra_raw.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=velectra_raw["train"].column_names,
)

# 2.3 Setup Model & Trainer
model_velectra = AutoModelForTokenClassification.from_pretrained(
    model_checkpoint_velectra,
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

    print("\nvELECTRA NER Classification Report:")
    print(classification_report(true_labels, true_preds, digits=4))

    return {
        "precision": precision_score(true_labels, true_preds),
        "recall": recall_score(true_labels, true_preds),
        "f1": f1_score(true_labels, true_preds),
    }

args_velectra = TrainingArguments(
    output_dir="/content/drive/MyDrive/models/velectra_ner",
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
    save_total_limit=2,
    report_to="none",
)

# Dùng Trainer mặc định. Không dùng WeightedTokenTrainer trong baseline sau khi đã sửa dataset.
trainer_velectra = Trainer(
    model=model_velectra,
    args=args_velectra,
    train_dataset=velectra_dataset["train"],
    eval_dataset=velectra_dataset["validation"],
    processing_class=tokenizer_velectra,
    data_collator=DataCollatorForTokenClassification(tokenizer_velectra),
    compute_metrics=compute_metrics_velectra,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.002)],
)"""

train_velectra_src = """# Chạy cell này khi muốn train vELECTRA NER
trainer_velectra.train()
trainer_velectra.save_model("/content/drive/MyDrive/models/velectra_ner")"""

nb["cells"] = [
    code_cell(install_src),
    code_cell(drive_src),
    md_cell("# Load dataset riêng cho từng task"),
    code_cell(load_src),
    md_cell("# 1. Huấn luyện PhoBERT-large cho Aspect-based Sentiment"),
    code_cell(phobert_src),
    code_cell(train_phobert_src),
    md_cell("# 2. Huấn luyện vELECTRA cho NER / Aspect Extraction"),
    code_cell(velectra_src),
    code_cell(train_velectra_src),
]

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Đã vá notebook thành công: {notebook_path}")
