import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
import pathlib

nb = new_notebook()

nb.cells.extend([
    new_markdown_cell("# Finetune vELECTRA và PhoBERT trên Google Colab\n\nNotebook này thực hiện Fine-tuning mô hình dựa trên dữ liệu chuẩn HuggingFace đã export."),
    new_code_cell("# Bước 1: Kết nối với Google Drive\nfrom google.colab import drive\ndrive.mount('/content/drive')"),
    new_code_cell("# Bước 2: Cài đặt thư viện cần thiết\n!pip install transformers datasets evaluate accelerate seqeval underthesea"),
    new_code_cell("# Bước 3: Đọc dataset từ Google Drive\nfrom datasets import load_dataset\n\ndata_files = {\n    'train': '/content/drive/MyDrive/dataset_hf/train.jsonl',\n    'validation': '/content/drive/MyDrive/dataset_hf/val.jsonl'\n}\nraw_datasets = load_dataset('json', data_files=data_files)\nprint(raw_datasets)"),
    new_markdown_cell("## 1. Huấn luyện PhoBERT (Sentiment Classification)"),
    new_code_cell(r'''import numpy as np
from transformers import (
    AutoModelForSequenceClassification, AutoTokenizer,
    DataCollatorWithPadding, Trainer, TrainingArguments
)

# 1.1 Khởi tạo Tokenizer
model_checkpoint_phobert = "vinai/phobert-base"
tokenizer_phobert = AutoTokenizer.from_pretrained(model_checkpoint_phobert)

_MAX_LEN = 256
_LABELS = ["positive", "negative", "neutral"]
_LABEL2ID = {label: i for i, label in enumerate(_LABELS)}
_ID2LABEL = {i: label for label, i in _LABEL2ID.items()}

# 1.2 Hàm Tokenize
def tokenize_phobert(batch):
    # Lọc bỏ Aspect "NONE"
    return tokenizer_phobert(
        [s for s in batch["aspect_label"]],
        [s for s in batch["sentence"]],
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )

def prepare_phobert_dataset(batch):
    filtered = [i for i, aspect in enumerate(batch["aspect_label"]) if aspect != "NONE"]
    if not filtered:
        return {"input_ids": [], "attention_mask": [], "labels": []}
    
    sentences = [batch["sentence"][i] for i in filtered]
    aspects = [batch["aspect_label"][i] for i in filtered]
    labels = [_LABEL2ID.get(batch["sentiment_label"][i], 2) for i in filtered]
    
    tokenized = tokenizer_phobert(
        aspects,
        sentences,
        truncation=True,
        max_length=_MAX_LEN,
        padding=False,
    )
    tokenized["labels"] = labels
    return tokenized

phobert_dataset = raw_datasets.map(
    prepare_phobert_dataset, 
    batched=True, 
    remove_columns=raw_datasets["train"].column_names
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
    learning_rate=2e-5,
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
    tokenizer=tokenizer_phobert,
    data_collator=DataCollatorWithPadding(tokenizer_phobert),
    compute_metrics=compute_metrics_phobert,
)'''),
    new_code_cell("# trainer_phobert.train()\n# trainer_phobert.save_model('/content/drive/MyDrive/models/phobert_sentiment')"),
    new_markdown_cell("## 2. Huấn luyện vELECTRA (Aspect Extraction)"),
    new_code_cell(r'''from seqeval.metrics import f1_score
from transformers import (
    AutoModelForTokenClassification, DataCollatorForTokenClassification
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

velectra_dataset = raw_datasets.map(
    tokenize_and_align_labels, batched=True, remove_columns=raw_datasets["train"].column_names
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
    return {"f1": f1_score(true, pred)}

args_velectra = TrainingArguments(
    output_dir="/content/drive/MyDrive/models/velectra_aspect",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1"
)

trainer_velectra = Trainer(
    model=model_velectra,
    args=args_velectra,
    train_dataset=velectra_dataset["train"],
    eval_dataset=velectra_dataset["validation"],
    tokenizer=tokenizer_velectra,
    data_collator=DataCollatorForTokenClassification(tokenizer_velectra),
    compute_metrics=compute_metrics_velectra,
)'''),
    new_code_cell("# trainer_velectra.train()\n# trainer_velectra.save_model('/content/drive/MyDrive/models/velectra_aspect')"),
])

with open("nlp/training/Colab_Finetuning_Template.ipynb", "w", encoding="utf-8") as f:
    nbformat.write(nb, f)
