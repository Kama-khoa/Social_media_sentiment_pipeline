import json
from pathlib import Path

p = Path(r'f:\Studies\Đồ án tốt nghiệp\Social_media_sentiment_pipeline\nlp\training\Colab_Finetuning_Template.ipynb')
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)

# Find cell indices
install_cell_idx = 0
load_data_cell_idx = 2
phobert_cell_idx = 4
velectra_cell_idx = 6

# 1. Pip install
d['cells'][install_cell_idx]['source'] = [
    "!pip install transformers datasets seqeval evaluate accelerate -q\n",
    "!pip install underthesea pyvi -q"
]

# 2. Load data
d['cells'][load_data_cell_idx]['source'] = [
    "from datasets import load_dataset\n",
    "\n",
    "# Dataset PhoBERT Sentiment\n",
    "phobert_files = {\n",
    "    \"train\": \"/content/drive/MyDrive/dataset_hf/sentiment/phobert/train.jsonl\",\n",
    "    \"validation\": \"/content/drive/MyDrive/dataset_hf/sentiment/phobert/val.jsonl\"\n",
    "}\n",
    "phobert_raw = load_dataset(\"json\", data_files=phobert_files)\n",
    "\n",
    "# Dataset vELECTRA NER\n",
    "velectra_files = {\n",
    "    \"train\": \"/content/drive/MyDrive/dataset_hf/ner/velectra/train.jsonl\",\n",
    "    \"validation\": \"/content/drive/MyDrive/dataset_hf/ner/velectra/val.jsonl\"\n",
    "}\n",
    "velectra_raw = load_dataset(\"json\", data_files=velectra_files)\n",
    "\n",
    "print(\"PhoBERT Dataset:\", phobert_raw)\n",
    "print(\"vELECTRA Dataset:\", velectra_raw)"
]

# 3. PhoBERT Setup
phobert_source = """import numpy as np
from transformers import (
    AutoModelForSequenceClassification, AutoTokenizer,
    DataCollatorWithPadding, Trainer, TrainingArguments, EarlyStoppingCallback
)
from pyvi import ViTokenizer

# 1.1 Khởi tạo Tokenizer
model_checkpoint_phobert = "vinai/phobert-large"
tokenizer_phobert = AutoTokenizer.from_pretrained(model_checkpoint_phobert)

_MAX_LEN = 256
_LABELS = ["positive", "negative", "neutral"]
_LABEL2ID = {label: i for i, label in enumerate(_LABELS)}
_ID2LABEL = {i: label for label, i in _LABEL2ID.items()}

# 1.2 Hàm Tokenize
def prepare_phobert_dataset(batch):
    # Word segmentation với pyvi
    sentences = [ViTokenizer.tokenize(str(text)) for text in batch["text"]]
    aspects = batch["aspect"]
    labels = [_LABEL2ID.get(lbl, 2) for lbl in batch["label"]]

    tokenized = tokenizer_phobert(
        aspects,
        sentences,
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )
    tokenized["labels"] = labels
    return tokenized

phobert_dataset = phobert_raw.map(
    prepare_phobert_dataset,
    batched=True,
    remove_columns=phobert_raw["train"].column_names
)

# 1.3 Setup Model & Trainer
model_phobert = AutoModelForSequenceClassification.from_pretrained(
    model_checkpoint_phobert, num_labels=len(_LABELS), id2label=_ID2LABEL, label2id=_LABEL2ID
)

def compute_metrics_phobert(eval_pred):
    from sklearn.metrics import f1_score
    preds = np.argmax(eval_pred.predictions, axis=-1)
    return {"f1": f1_score(eval_pred.label_ids, preds, average="macro")}

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
    load_best_model_at_end=True,
    metric_for_best_model="f1"
)

trainer_phobert = Trainer(
    model=model_phobert,
    args=args_phobert,
    train_dataset=phobert_dataset["train"],
    eval_dataset=phobert_dataset["validation"],
    processing_class=tokenizer_phobert,
    data_collator=DataCollatorWithPadding(tokenizer_phobert),
    compute_metrics=compute_metrics_phobert,
)
"""
d['cells'][phobert_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in phobert_source.splitlines()]

# 4. vELECTRA Setup
velectra_source = """from seqeval.metrics import f1_score, precision_score, recall_score, classification_report
from transformers import (
    AutoModelForTokenClassification, DataCollatorForTokenClassification, EarlyStoppingCallback, Trainer
)

# 2.1 Cấu hình Labels
_ASPECT_LABELS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]
_LABEL_LIST = ["O"] + [f"{p}-{a}" for a in _ASPECT_LABELS for p in ("B", "I")]
_LABEL2ID_VEL = {label: i for i, label in enumerate(_LABEL_LIST)}
_ID2LABEL_VEL = {i: label for label, i in _LABEL2ID_VEL.items()}

model_checkpoint_velectra = "FPTAI/velectra-base-discriminator-cased"
tokenizer_velectra = AutoTokenizer.from_pretrained(model_checkpoint_velectra)

# 2.2 Align Tokens & Labels
def tokenize_and_align_labels(batch):
    tokenized = tokenizer_velectra(
        batch["tokens"], truncation=True, is_split_into_words=True, max_length=_MAX_LEN
    )
    aligned_labels = []
    for i, label_seq in enumerate(batch["ner_tags"]):
        word_ids = tokenized.word_ids(batch_index=i)
        prev = None
        ids = []
        for wid in word_ids:
            if wid is None:
                ids.append(-100)
            elif wid != prev:
                ids.append(_LABEL2ID_VEL.get(label_seq[wid], 0))
            else:
                ids.append(-100)
            prev = wid
        aligned_labels.append(ids)
    tokenized["labels"] = aligned_labels
    return tokenized

velectra_dataset = velectra_raw.map(
    tokenize_and_align_labels, batched=True, remove_columns=velectra_raw["train"].column_names
)

# 2.3 Setup Model & Trainer
model_velectra = AutoModelForTokenClassification.from_pretrained(
    model_checkpoint_velectra, num_labels=len(_LABEL_LIST), id2label=_ID2LABEL_VEL, label2id=_LABEL2ID_VEL
)

def compute_metrics_velectra(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    true = [[_LABEL_LIST[l] for l in row if l != -100] for row in labels]
    pred = [[_LABEL_LIST[p] for p, l in zip(p_row, l_row) if l != -100] for p_row, l_row in zip(preds, labels)]
    
    # In ra báo cáo chi tiết cho từng class
    print("\\nNER Classification Report:")
    print(classification_report(true, pred))
    
    return {
        "precision": precision_score(true, pred),
        "recall": recall_score(true, pred),
        "f1": f1_score(true, pred)
    }

args_velectra = TrainingArguments(
    output_dir="./velectra-ner",
    num_train_epochs=10,
    learning_rate=1e-5,
    warmup_ratio=0.1,
    weight_decay=0.01,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    save_total_limit=2,
    report_to="none"
)

trainer_velectra = Trainer(
    model=model_velectra,
    args=args_velectra,
    train_dataset=velectra_dataset["train"],
    eval_dataset=velectra_dataset["validation"],
    processing_class=tokenizer_velectra,
    data_collator=DataCollatorForTokenClassification(tokenizer_velectra),
    compute_metrics=compute_metrics_velectra,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.002)]
)
"""
d['cells'][velectra_cell_idx]['source'] = [line + '\n' if not line.endswith('\n') else line for line in velectra_source.splitlines()]

with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=1, ensure_ascii=False)

print("Đã vá file Colab_Finetuning_Template.ipynb thành công!")
