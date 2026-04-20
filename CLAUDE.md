# CLAUDE.md — Social Media Sentiment Pipeline

## Tổng quan dự án

**Tên:** Social Media Sentiment Pipeline
**Mục tiêu:** Hệ thống thu thập bình luận YouTube về sản phẩm công nghệ Việt Nam (điện thoại, laptop, tai nghe, thiết bị smarthome), phân tích cảm xúc đa chiều theo từng khía cạnh sản phẩm, và hiển thị insight qua dashboard tương tác.

**Đây là đồ án tốt nghiệp** — output phải đạt cả tiêu chuẩn kỹ thuật lẫn học thuật.

---

## Kiến trúc tổng thể: ELT

```
YouTube / RSS
     │
     ▼ Extract (elt/extract/)
  GCS Bucket                  ← Data Lake, lưu JSON thô
  product-sentiment-raw-1806
  raw/youtube/YYYY/MM/DD/
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
| Data Lake | Google Cloud Storage (`social-media-sentiment-raw`) |
| Data Warehouse | BigQuery (dataset: `sentiment_platform`) |
| Orchestration | Apache Airflow 3.1.8 (Docker, Python 3.13) |
| Data Transform | dbt-bigquery |
| Video discovery | yt-dlp, feedparser (RSS), YouTube Data API v3 |
| Comment collection | youtube-comment-downloader, BrightData Residential Proxy |
| Vietnamese NLP | underthesea (word segmentation) |
| Aspect extraction | vELECTRA (fine-tuned, Token Classification) |
| Sentiment | PhoBERT (fine-tuned, Sequence Classification) |
| LLM fallback | Gemini 2.5 Flash (confidence routing < 0.80) |
| Change point | ruptures (PELT algorithm) |
| API | FastAPI + Redis cache (TTL=300s) |
| Dashboard | Streamlit |
| Training | Google Colab (GPU T4 16GB) |
| ETL runtime | Python 3.13.12 |

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
├── bucket_search: 9,000  → video discovery (Mode 0 + 1 + 2)
└── bucket_channel:  500  → channels.list khi seed kênh mới

COMMENTS: 0 API units → youtube-comment-downloader
```

**3 Mode Discovery:**
- **Mode 0** — Historical Scan: `search.list(channelId, keyword)` × 4 keywords, 400 units/kênh, chạy 1 lần/kênh
- **Mode 1** — RSS Daily: `feedparser` đọc RSS feed kênh, 0 units, 15 video/kênh
- **Mode 2** — Keyword Sweep: `search.list(q=keyword)` global, 400 units/ngày

---

## GCS Partition Convention

```
gs://product-sentiment-raw-1806/raw/youtube/YYYY/MM/DD/keyword_HHMMSS.json
```

Tuân thủ convention này để BigQuery External Table partition đúng.

---

## BigQuery Schema — 12 bảng

| Layer | Bảng |
|---|---|
| Layer 0 Config | `keyword_config`, `channel_config`, `video_crawl_state`, `quota_daily_summary`, `quota_operation_log` |
| Layer 1 Raw | `raw_videos`, `raw_comments` (External Tables → GCS) |
| Layer 2 Staging | `stg_youtube_videos`, `stg_youtube_comments` |
| Layer 3 Intermediate | `int_comment_sentences`, `int_sentiment_results` |
| Layer 4 Marts | `dim_products`, `fact_product_mentions`, `agg_daily_product_ranking` |

---

## Quy tắc bắt buộc khi code

1. **ETL Python** (`elt/`) chạy Python 3.13.12 — KHÔNG dùng Airflow imports trong đây
2. **Airflow DAGs** (`airflow/`) chạy Docker Python 3.13 — chỉ import và gọi ETL scripts
3. ETL và Airflow phải **hoàn toàn tách biệt**
4. Không comment trong code — code phải tự nói lên ý nghĩa
5. Mỗi class nằm trong file riêng
6. Thông tin nhạy cảm luôn đọc từ `.env`, không bao giờ hardcode
7. `underthesea` word segmentation phải chạy **trước** khi đưa text vào PhoBERT
8. Confidence routing threshold = **0.80** — dưới ngưỡng này gửi sang Gemini Flash

---

## Cấu trúc thư mục

```
Social_media_sentiment_pipeline/
├── .env                    ← credentials (không commit)
├── .env.example            ← template public
├── .gitignore
├── requirements.txt        ← ETL environment (Python 3.13.12)
├── config/
│   └── pipeline_config.yaml
├── schema/                 ← khởi tạo BQ schema theo layer
├── elt/                    ← Extract + Load → GCS
├── transform/              ← dbt: GCS → BigQuery
├── nlp/                    ← NLP pipeline
├── analytics/              ← ranking + attribution engine
├── api/                    ← FastAPI
├── dashboard/              ← Streamlit
├── airflow/                ← DAGs (tạo sau phase 1)
└── tests/
```
