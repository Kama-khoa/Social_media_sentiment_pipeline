# CLAUDE.md — Social Media Sentiment Pipeline

## Tổng quan dự án

**Tên:** Social Media Sentiment Pipeline
**Mục tiêu:** Hệ thống thu thập bình luận YouTube về sản phẩm công nghệ Việt Nam (điện thoại, laptop, tai nghe, thiết bị smarthome), phân tích cảm xúc đa chiều theo từng khía cạnh sản phẩm, và hiển thị insight qua dashboard tương tác.

**Đây là đồ án tốt nghiệp** — output phải đạt cả tiêu chuẩn kỹ thuật lẫn học thuật.

---

## Kiến trúc tổng thể: ELT

```
YouTube Data API / yt-dlp
     │
     ▼ Extract (elt/extract/)
  GCS Bucket                  ← Data Lake, lưu JSON thô
  product-sentiment-raw-1806
  raw/videos/YYYY/MM/DD/
  raw/comments/YYYY/MM/DD/
     │
     ▼ Load (schema/layer_1_raw/)
  BigQuery External Tables     ← đọc trực tiếp từ GCS
     │
     ▼ Transform (transform/)
  BigQuery Managed Tables
  ├── Layer 2: Staging
  ├── Layer 3: Intermediate
  └── Layer 4: Marts
     │
     ▼
  NLP Pipeline (nlp/)          ← chạy trên dữ liệu đã transform
     │
     ▼
  Analytics Engine (analytics/)
     │
     ▼
  FastAPI + Streamlit (api/ + dashboard/)
```

---

## Thứ tự phát triển theo phase

| Phase | Folder | Mô tả |
|---|---|---|
| 0 | `schema/` | Khởi tạo toàn bộ BQ schema trước khi làm bất cứ thứ gì |
| 1 | `elt/` | Thu thập dữ liệu → GCS. Xong phase này mới tạo DAG |
| 2 | `transform/` | dbt biến đổi raw → Staging → Intermediate → Marts |
| 3 | `nlp/` | Auto-annotation → Training (Colab) → Local inference |
| 4 | `analytics/` | Bayesian ranking, Controversy index, PELT attribution |
| 5 | `api/` + `dashboard/` | FastAPI backend + Streamlit frontend |
| 6 | `airflow/` | DAG automation — TẠO SAU KHI phase 1 chạy thành công |

---

## Tech stack toàn dự án

| Lớp | Công nghệ |
|---|---|
| Data Lake | Google Cloud Storage (`product-sentiment-raw-1806`) |
| Data Warehouse | BigQuery (dataset: `sentiment_platform`) |
| Orchestration | Manual execution via Conda etl-py313 (Airflow chuyển đổi sang Local) |
| Data Transform | dbt-bigquery |
| Video discovery | yt-dlp, YouTube Data API v3 (`search.list`) |
| Comment collection | youtube-comment-downloader, BrightData Residential Proxy |
| Vietnamese NLP | underthesea (cho vELECTRA), pyvi (cho PhoBERT) |
| Aspect extraction | vELECTRA (fine-tuned, Token Classification) |
| Sentiment | PhoBERT (fine-tuned, Sequence Classification) |
| LLM fallback | Gemini Flash (confidence routing < 0.70) |
| Change point | ruptures (PELT algorithm) |
| API | FastAPI + Redis cache (TTL=300s) |
| Dashboard | Streamlit |
| Training | Google Colab (GPU T4 16GB) |
| ETL runtime | Conda environment: etl-py313 (Python 3.13) |

---

## Môi trường và biến nhạy cảm

Tất cả credentials nằm trong `.env` ở root. **Không bao giờ hardcode.**

```
GCP_PROJECT_ID
GCS_BUCKET_NAME=product-sentiment-raw-1806
BQ_DATASET=sentiment_platform
GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account.json>
YOUTUBE_API_KEY
GEMINI_API_KEY
BRIGHTDATA_PROXY_HOST
BRIGHTDATA_PROXY_PORT
BRIGHTDATA_USERNAME
BRIGHTDATA_PASSWORD
```

Load bằng `python-dotenv`: `from dotenv import load_dotenv; load_dotenv()`

---

## Quota YouTube API

**Giới hạn:** 10,000 units/ngày

```
TỔNG: 10,000 units/ngày
├── safety_buffer:   500  (không dùng)
├── bucket_search: 9,000  → video discovery (Phase A daily + Phase B historical)
└── bucket_channel:  500  → channels.list khi seed kênh mới

COMMENTS: 0 API units → youtube-comment-downloader
```

**2-Mode Discovery:**
- **Phase A — Daily Scan:** `search.list(channelId, order=date, publishedAfter=3 ngày trước)` per channel, 100 units/channel, 18 channels = 1,800 units/ngày. Filter keyword local. Enrich bằng yt-dlp (0 quota)
- **Phase B — Historical Scan:** yt-dlp `extract_flat=True` lấy toàn bộ video cũ từ channel, 0 units, chạy 1 lần/kênh. Enrich bằng yt-dlp (0 quota)

**Quota budget hằng ngày (sau khi tất cả channel đã historical scan):**
```
Phase A search.list:   1,800 units
Phase B (skip):            0 units
Tổng:                  1,800 units → còn 7,700 dự phòng
```

---

## Pipeline Schedule

Airflow DAG chạy lúc **2:00 AM UTC+7 hằng ngày**.

```
Phase A — DAILY: search.list 18 channels → filter keyword → dedupe → enrich yt-dlp → save → comment crawl
Phase B — HISTORICAL: yt-dlp scan kênh chưa scan → batch 50 → enrich → save → comment crawl (interleaved)
Phase C — BACKLOG: recrawl comments theo Video Maturity Model (priority scoring)
```

---

## Data Integrity Principle

**GCS-first, BQ-second:** Ghi dữ liệu lên GCS trước, chốt trạng thái vào BQ sau. Nếu BQ fail sau GCS success → retry sẽ tạo duplicate GCS file (dbt layer dedupe by video_id). Nếu BQ success trước GCS fail → mất dữ liệu vĩnh viễn.

---

## GCS Partition Convention

```
gs://social-media-sentiment-raw/raw/videos/YYYY/MM/DD/videos_run_HHMMSS.json
gs://social-media-sentiment-raw/raw/comments/YYYY/MM/DD/comments_{video_id}_HHMMSS.json
```

Tuân thủ convention này để BigQuery External Table partition đúng.

---

## BigQuery Schema — 12 bảng

| Layer | Bảng |
|---|---|
| Layer 0 Config | `keyword_config`, `channel_config`, `video_crawl_state`, `quota_daily_summary`, `quota_operation_log` |
| Layer 1 Raw | `raw_videos`, `raw_comments` (External Tables → GCS), `raw_sentiment_results` |
| Layer 2 Staging | `stg_youtube_videos`, `stg_youtube_comments` |
| Layer 3 Intermediate | `int_comment_sentences`, `int_sentiment_results` |
| Layer 4 Marts | `dim_products`, `fact_product_mentions`, `agg_daily_product_ranking` |

---

## Quy tắc bắt buộc khi code

1. **ETL Python** (`elt/`) chạy trên Conda environment `etl-py313` — KHÔNG dùng Airflow imports trong đây
2. **Airflow DAGs** (`airflow/`) đang chuyển sang môi trường Local (trước đây là Docker) để tránh overload, ưu tiên chạy manual qua script trong giai đoạn dev.
3. ETL và Airflow phải **hoàn toàn tách biệt**
4. Không comment trong code — code phải tự nói lên ý nghĩa
5. Mỗi class nằm trong file riêng
6. Thông tin nhạy cảm luôn đọc từ `.env`, không bao giờ hardcode
7. PhoBERT yêu cầu tách từ bằng `pyvi` (`ViTokenizer`) và format input `aspect </s> sentence`. vELECTRA dùng `underthesea` để tách âm tiết và căn chỉnh nhãn BIO.
8. Confidence routing threshold = **0.70** — dưới ngưỡng này gửi sang Gemini Flash. Ngưỡng này đã được debug trên 500 sentences local, fallback tổng khoảng 6%.
9. **GCS-first, BQ-second** — ghi data lake trước, chốt trạng thái sau
10. Không sử dụng icons quá nhiều trong code hoặc tài liệu

---

## Cấu trúc thư mục

```text
Social_media_sentiment_pipeline/
├── .env                    ← credentials (không commit)
├── .env.example            ← template public
├── .gitignore
├── requirements.txt        ← ETL environment (Python 3.13.12)
├── run_dbt.bat             ← Lệnh chạy thủ công dbt trên Windows (gọi scripts/dbt/dbt_runner.py)
├── config/
│   └── pipeline_config.yaml
├── schema/                 ← khởi tạo BQ schema theo layer
├── elt/                    ← Extract + Load → GCS (Lưu ý: ghi NDJSON cho BigQuery External Tables)
├── transform/              ← dbt: GCS → BigQuery
├── nlp/                    ← NLP pipeline
├── analytics/              ← ranking + attribution engine
├── api/                    ← FastAPI
├── dashboard/              ← Streamlit
├── airflow/                ← DAGs (tạo sau phase 1)
├── scripts/                ← Script tiện ích / bảo trì
│   ├── dbt/                ← Script chạy dbt thủ công (dbt_runner.py)
│   └── maintenance/        ← Các script fix data GCS, xử lý lỗi BigQuery
└── tests/
```

---

## Lưu ý Kỹ Thuật Quan Trọng Mới Cập Nhật

1. **Định dạng NDJSON cho GCS**: BigQuery External Tables (`raw_videos`, `raw_comments`) yêu cầu dữ liệu JSON lưu trên GCS phải là chuẩn **Newline Delimited JSON (NDJSON)**. Code trong `elt/datacontext/gcs_client.py` đã được thiết kế để tự động convert sang NDJSON khi upload.
2. **Location BigQuery**: Tất cả dataset của project phải được đặt ở **`asia-southeast1`** (kể cả staging/marts của dbt) để đồng bộ với dataset gốc do pipeline sinh ra.
3. **Chạy thủ công dbt**: Để chạy dbt ngoài môi trường Airflow (debug/dev), hãy sử dụng file `run_dbt.bat` ở thư mục gốc, file này sẽ nạp `.env` và gọi script `scripts/dbt/dbt_runner.py` để chạy dbt an toàn.

---

## Cập Nhật 2026-05-30 — NLP Phase

Phase 3 NLP đã đủ điều kiện vận hành end-to-end:

- `models/phobert_sentiment` và `models/velectra_aspect` đã được đồng bộ local và load ổn định.
- `VELECTRAExtractor` dùng `underthesea`, có fallback tokenizer cho checkpoint vELECTRA Colab.
- `PhoBERTClassifier` dùng `pyvi` và model local `models/phobert_sentiment`.
- `ConfidenceRouter` dùng threshold `0.70`, lazy-load Gemini fallback, xử lý `NONE` aspect thành `neutral` mà không gọi PhoBERT.
- Debug local confidence trên 500 sentences: fallback tổng khoảng `6%`, fallback trên aspect thật khoảng `15.8%`; nguyên nhân chính là sentiment confidence thấp, NER nhìn chung ổn.
- `nlp.runner` đã có batch inference, debug mode, `--reprocess`, và ghi `raw_sentiment_results` bằng BigQuery `MERGE` theo `result_id`.
- dbt flow đã nối: `raw_sentiment_results` -> `int_sentiment_results` -> `fact_product_mentions`.
- Airflow `sentiment_analysis_dag` đã gọi `nlp.runner`, sau đó promote kết quả bằng dbt.

Lệnh vận hành thủ công khuyến nghị:

```powershell
python -m nlp.runner --limit 500 --dag-run-id manual-nlp-500-t070
cd transform
python -m dotenv -f ..\.env run -- dbt run --profiles-dir . --select int_sentiment_results fact_product_mentions
```

Khi cần chạy lại bằng model/threshold mới:

```powershell
python -m nlp.runner --limit 500 --dag-run-id reprocess-t070 --reprocess
```

Phase tiếp theo: hoàn thiện Analytics Engine trên dữ liệu `fact_product_mentions`, ưu tiên Bayesian ranking, controversy index, sau đó PELT attribution.
