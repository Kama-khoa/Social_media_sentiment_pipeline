# CLAUDE.md — nlp/

## Mục tiêu

Xây dựng pipeline NLP hybrid để phân tích cảm xúc theo khía cạnh (Aspect-Based Sentiment Analysis) cho bình luận tiếng Việt về sản phẩm công nghệ. Gồm 3 giai đoạn: Auto-Annotation → Cloud Training → Local Inference.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `annotation/gemini_annotator.py` | `GeminiAnnotator` class — gửi batch 50 câu/request tới Gemini API, nhận về nhãn BIO có cấu trúc JSON |
| `annotation/prompt_builder.py` | `PromptBuilder` class — xây dựng few-shot prompt theo format chuẩn cho Gemini, định nghĩa 6 aspect labels |
| `training/prepare_dataset_v2.py` | Script chuẩn bị dữ liệu — gộp các file JSON thành `labeled_master.jsonl`, gộp nhãn BIO cho từng câu, loại bỏ các lỗi BIO/span dài/conflict nhãn, mix 20-30% nhãn NONE, split train/val tránh data leakage |
| `training/Colab_Finetuning_Template.ipynb` | Notebook chạy trên Google Colab — fine-tune PhoBERT (sentiment classification) và vELECTRA (token classification) |
| `training/upload_to_drive.py` | Script upload dataset và model checkpoints lên Google Drive |
| `inference/phobert_classifier.py` | `PhoBERTClassifier` class — load weights PhoBERT local, predict sentiment score + confidence |
| `inference/velectra_extractor.py` | `VELECTRAExtractor` class — load weights vELECTRA local, extract aspect spans từ câu |
| `inference/confidence_router.py` | `ConfidenceRouter` class — điều phối: nếu local confidence < 0.70 → gom batch fallback sang Gemini Flash |
| `runner.py` | Batch inference runner — đọc `int_comment_sentences`, chạy vELECTRA + PhoBERT + confidence routing, upsert vào `raw_sentiment_results` |

---

## Luồng hoạt động

### Giai đoạn 1: Auto-Annotation & Data Preparation (chạy thủ công 1 lần)

```
BigQuery: int_comment_sentences
    │ lấy các câu sạch nhất
    ▼
annotation/prompt_builder.py
    │ xây dựng few-shot prompt với 6 aspect labels
    ▼
annotation/gemini_annotator.py
    │ batch 20-50 câu/request → Gemini 1.5 Flash API
    │ nhận JSON: [{sentence, aspect, bio_tags, sentiment}]
    ▼
gemini_annotated_*.json (raw outputs)
    │
    ▼ training/prepare_dataset_v2.py
    ├── Gộp thành master/labeled_master.jsonl
    ├── Group theo câu, giải quyết xung đột nhãn & validation BIO
    ├── Thêm 20-30% câu NONE thật (tránh False Positive cho NER)
    ├── Chia Train/Val theo câu (no overlap → tránh Data Leakage)
    ▼
dataset_hf/
├── sentiment/phobert/ (train.jsonl, val.jsonl)
└── ner/velectra/ (train.jsonl, val.jsonl)
```

### Giai đoạn 2: Cloud Training (chạy trên Google Colab)

```
dataset_hf/ → Google Drive
    │
    ▼ training/Colab_Finetuning_Template.ipynb
    ├── Fine-tune PhoBERT (PhoBERT-large, input format: aspect </s> sentence, word segmented by pyvi)
    └── Fine-tune vELECTRA (vielectra-base, default Trainer, early stopping)
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
    ├── confidence >= 0.70 → ghi kết quả vào raw_sentiment_results
    │
    └── confidence < 0.70
            ▼
        inference/confidence_router.py
            │ gom các câu fallback theo batch cấu hình → Gemini Flash API
            ▼
        kết quả Gemini → raw_sentiment_results → int_sentiment_results
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

## Cập Nhật 2026-05-30 — Trạng Thái NLP

NLP phase đã hoàn chỉnh ở mức vận hành:

- PhoBERT sentiment: best validation macro F1 khoảng `0.804`, đủ gate dự án.
- vELECTRA NER boundary dataset: entity F1 khoảng `0.90`, model local load ổn định.
- Local smoke tests pass cho `PhoBERTClassifier`, `VELECTRAExtractor`, `ConfidenceRouter`.
- `ConfidenceRouter` đọc `nlp.confidence_threshold` và `nlp.gemini_batch_size` từ `config/pipeline_config.yaml`; Gemini fallback chỉ lazy-load khi cần và gom batch toàn bộ câu confidence thấp trong mỗi lần chạy runner.
- Debug `scratch/local_confidence_debug_500_t070.jsonl`: 500 sentences, fallback tổng `6.0%`, fallback aspect thật `15.8%`.
- `nlp.runner` hỗ trợ batch inference từ BigQuery, debug confidence, dry-run JSONL, reprocess, và BigQuery MERGE/upsert vào `raw_sentiment_results`.
- dbt promote kết quả qua `int_sentiment_results`, sau đó `fact_product_mentions`.

Lệnh kiểm tra nhanh:

```powershell
python -m nlp.runner --limit 100 --debug-local-confidence --output-jsonl scratch\local_confidence_debug_check.jsonl
python -m nlp.runner --limit 100 --dag-run-id manual-nlp-100-t070
cd transform
python -m dotenv -f ..\.env run -- dbt run --profiles-dir . --select int_sentiment_results fact_product_mentions
```

- **Không dùng chung một cấu hình Tokenizer/Preprocessing** cho cả hai model:
  - **PhoBERT:** BẮT BUỘC word segmentation bằng `pyvi` (`ViTokenizer.tokenize`) trước khi tokenize. Định dạng đầu vào: `aspect` làm text_pair và `sentence` đã segmented làm text chính (sẽ được tokenizer ghép lại thành `aspect </s> sentence`).
  - **vELECTRA:** Dùng `underthesea.word_tokenize` để tách âm tiết (syllables) và aligns nhãn BIO.
- **Không split dữ liệu ngẫu nhiên theo dòng** cho tập NER/Sentiment: Phải group theo `sentence` trước khi split để tránh tình trạng cùng một câu xuất hiện ở cả tập Train và Val (Data Leakage).
- **vELECTRA NER Training:** Sử dụng `Trainer` mặc định của HuggingFace kết hợp Early Stopping. KHÔNG dùng `WeightedTokenTrainer` (vốn nhân đôi loss nhãn B/I) để hạn chế False Positive, thay vào đó hãy duy trì tỉ lệ nhãn NONE thật khoảng 20-30%.
- Model weights sau training lưu vào thư mục `models/` ở root (không commit weights vào git).
- Confidence threshold = **0.70** — giá trị này đã được chọn sau debug 500 sentences local: fallback tổng khoảng 6%, fallback trên aspect thật khoảng 15.8%.
- Few-shot prompting theo Brown et al. (2020) — mỗi prompt có ít nhất 3 examples mẫu.
- Gemini output phải là **JSON thuần** — prompt_builder.py phải enforce điều này.
