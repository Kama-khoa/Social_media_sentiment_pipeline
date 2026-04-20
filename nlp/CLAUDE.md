# CLAUDE.md — nlp/

## Mục tiêu

Xây dựng pipeline NLP hybrid để phân tích cảm xúc theo khía cạnh (Aspect-Based Sentiment Analysis) cho bình luận tiếng Việt về sản phẩm công nghệ. Gồm 3 giai đoạn: Auto-Annotation → Cloud Training → Local Inference.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `annotation/gemini_annotator.py` | `GeminiAnnotator` class — gửi batch 50 câu/request tới Gemini API, nhận về nhãn BIO có cấu trúc JSON |
| `annotation/prompt_builder.py` | `PromptBuilder` class — xây dựng few-shot prompt theo format chuẩn cho Gemini, định nghĩa 6 aspect labels |
| `training/finetune_phobert.py` | Script chạy trên Google Colab — fine-tune PhoBERT (vinai/phobert-base) cho Sequence Classification (3 nhãn: positive/negative/neutral) |
| `training/finetune_velectra.py` | Script chạy trên Google Colab — fine-tune vELECTRA cho Token Classification (nhận diện 6 aspect spans) |
| `inference/phobert_classifier.py` | `PhoBERTClassifier` class — load weights PhoBERT local, predict sentiment score + confidence |
| `inference/velectra_extractor.py` | `VELECTRAExtractor` class — load weights vELECTRA local, extract aspect spans từ câu |
| `inference/confidence_router.py` | `ConfidenceRouter` class — điều phối: nếu PhoBERT confidence < 0.80 → fallback sang Gemini Flash |

---

## Luồng hoạt động

### Giai đoạn 1: Auto-Annotation (chạy thủ công 1 lần)

```
BigQuery: int_comment_sentences
    │ lấy 2,000 câu sạch nhất
    ▼
annotation/prompt_builder.py
    │ xây dựng few-shot prompt với 6 aspect labels
    ▼
annotation/gemini_annotator.py
    │ batch 50 câu/request → Gemini 1.5 Flash API
    │ nhận JSON: [{sentence, aspect, bio_tags, sentiment}]
    ▼
dataset_bio_tagged.json          ← output: training dataset
    │
    ▼
underthesea.word_tokenize()      ← word segmentation bắt buộc
    ▼
dataset_tokenized.json
```

### Giai đoạn 2: Cloud Training (chạy trên Google Colab)

```
dataset_tokenized.json → Google Drive
    │
    ├── training/finetune_velectra.py  → vELECTRA weights (aspect extraction)
    └── training/finetune_phobert.py   → PhoBERT weights (sentiment classification)
    │
    ▼
weights/ tải về local
├── models/velectra_aspect/
└── models/phobert_sentiment/
```

### Giai đoạn 3: Local Inference (chạy hằng ngày)

```
BigQuery: int_comment_sentences (câu chưa có sentiment)
    │
    ▼
inference/velectra_extractor.py
    │ extract aspect spans → ["Pin", "Camera", ...]
    ▼
inference/phobert_classifier.py
    │ classify sentiment → {label: "positive", confidence: 0.91}
    │
    ├── confidence >= 0.80 → ghi kết quả vào int_sentiment_results
    │
    └── confidence < 0.80
            ▼
        inference/confidence_router.py
            │ fallback → Gemini 1.5 Flash API
            ▼
        kết quả Gemini → int_sentiment_results
```

---

## 6 Aspect Labels

| Label | Ví dụ câu |
|---|---|
| `Pin` | "Pin trâu lắm, dùng cả ngày không hết" |
| `Camera` | "Camera chụp đêm rất rõ nét" |
| `Màn hình` | "Màn hình sắc nét, xem phim đã mắt" |
| `Hiệu năng` | "Máy chạy mượt, không giật lag" |
| `Thiết kế` | "Thiết kế sang, cầm chắc tay" |
| `Giá` | "Giá hơi cao so với cấu hình" |

---

## Thông tin bảo mật

| Biến | Dùng trong | Mục đích |
|---|---|---|
| `GEMINI_API_KEY` | `gemini_annotator.py`, `confidence_router.py` | Gọi Gemini API |
| `GCP_PROJECT_ID`, `BQ_DATASET` | tất cả inference files | Đọc/ghi BigQuery |
| `GOOGLE_APPLICATION_CREDENTIALS` | tất cả inference files | GCP auth |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng trong | Mục đích |
|---|---|---|---|
| `google-generativeai` | 0.8.3 | annotation, routing | Gemini API |
| `underthesea` | 6.8.4 | annotation, inference | Word segmentation tiếng Việt |
| `torch` | 2.6.0 | training, inference | Deep learning framework |
| `transformers` | 4.48.0 | training, inference | PhoBERT + vELECTRA |
| `sentencepiece` | 0.2.0 | inference | PhoBERT tokenizer |
| `google-cloud-bigquery` | 3.27.0 | inference | Đọc/ghi BQ |

---

## Lưu ý quan trọng

- **underthesea PHẢI chạy trước** khi đưa text vào PhoBERT tokenizer
- `training/` scripts thiết kế để chạy trên **Google Colab** (GPU T4 16GB) — không chạy local
- Model weights sau training lưu vào thư mục `models/` ở root (không commit weights vào git)
- Confidence threshold = **0.80** — không thay đổi giá trị này nếu không có lý do học thuật
- Few-shot prompting theo Brown et al. (2020) — mỗi prompt có ít nhất 3 examples mẫu
- Gemini output phải là **JSON thuần** — prompt_builder.py phải enforce điều này
