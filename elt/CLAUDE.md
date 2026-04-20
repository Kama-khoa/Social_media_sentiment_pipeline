# CLAUDE.md — elt/

## Mục tiêu

Extract dữ liệu từ YouTube (video metadata + comments) và Load thẳng vào **Google Cloud Storage** dưới dạng JSON thô.
Đây là bước **E** và **L** của pipeline ELT — **không** có Transform ở đây.
Transform được thực hiện hoàn toàn bởi dbt trong folder `transform/`.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `config.py` | `PipelineConfig` dataclass — load toàn bộ config từ `config/pipeline_config.yaml` và `.env`. Entry point cấu hình cho toàn bộ ELT |
| `quota_budget.py` | `QuotaBudget` class — quản lý 10,000 YouTube API units/ngày theo 2 bucket: `search_videos` (9,000) và `channel_seed` (500). Raise `InsufficientQuotaError` khi vượt quota |
| `datacontext/gcs_client.py` | `GCSClient` class — kết nối GCS, upload JSON, kiểm tra file tồn tại. Mọi I/O với GCS đều đi qua đây |
| `datacontext/models/video_dto.py` | `VideoDTO` dataclass — cấu trúc dữ liệu video (video_id, title, channel_id, published_at, view_count, ...) |
| `datacontext/models/comment_dto.py` | `CommentDTO` dataclass — cấu trúc dữ liệu comment (comment_id, video_id, text, author, published_at, like_count) |
| `datacontext/models/channel_dto.py` | `ChannelDTO` dataclass — cấu trúc dữ liệu kênh (channel_id, name, subscriber_count, is_historically_scanned) |
| `seed_data/seed_loader.py` | Script chạy thủ công — đọc 2 file CSV và load vào BQ tables `channel_config` + `keyword_config` |
| `seed_data/seed_channels.csv` | Danh sách 26 kênh YouTube công nghệ Việt Nam (channel_id, name, subscriber_count) |
| `seed_data/seed_keywords.csv` | Danh sách keywords theo ~15 semantic cluster (keyword, cluster_name, product_category) |
| `extract/base_extractor.py` | `BaseExtractor` abstract class — định nghĩa interface chuẩn cho video và comment extraction |
| `extract/video_extractor.py` | `VideoExtractor` class — triển khai 3 mode discovery: Mode 0 (yt-dlp), Mode 1 (RSS), Mode 2 (search.list) |
| `extract/comment_extractor.py` | `CommentExtractor` class — crawl comments qua `youtube-comment-downloader` + BrightData proxy. 0 YouTube API quota |
| `repositories/channel_repository.py` | `ChannelRepository` — CRUD BigQuery table `channel_config`. Gồm `get_unscanned_channels()`, `mark_historically_scanned()` |
| `repositories/crawl_state_repository.py` | `CrawlStateRepository` — quản lý `video_crawl_state`: video nào đã crawl, cần crawl lại, Comment Count Gate |
| `repositories/quota_repository.py` | `QuotaRepository` — ghi log vào `quota_operation_log`, tổng hợp vào `quota_daily_summary`, query quota đã dùng theo bucket |

---

## Luồng hoạt động

```
config.py (load .env + pipeline_config.yaml)
    │
    ├── quota_budget.py ← query quota đã dùng hôm nay từ BQ
    │       quota_repository.py → BigQuery quota_operation_log
    │
    ├── seed_data/seed_loader.py (chạy thủ công 1 lần)
    │       seed_channels.csv → channel_repository → BQ channel_config
    │       seed_keywords.csv → BQ keyword_config
    │
    └── extract/ (chạy hằng ngày)
            │
            ├── video_extractor.py
            │   ├── Mode 0: yt-dlp → list video_id từ channel (0 API quota)
            │   ├── Mode 1: feedparser RSS → 15 video mới nhất/kênh (0 API quota)
            │   └── Mode 2: YouTube search.list → keyword sweep (100 units/call)
            │
            └── comment_extractor.py
                    youtube-comment-downloader + BrightData proxy
                    → crawl_state_repository (check Video Maturity)
                    → CommentDTO list
                    → gcs_client.upload()
                    → GCS: raw/videos/YYYY/MM/DD/videos_run_HHMMSS.json
                           raw/comments/YYYY/MM/DD/comments_{video_id}_HHMMSS.json
```

---

## Video Maturity Model

Trạng thái video quyết định tần suất crawl lại:

| Stage | Tuổi video | Crawl lại sau |
|---|---|---|
| new | < 3 ngày | Bỏ qua (Comment Count Gate) |
| growing | 3–14 ngày | 3 ngày |
| mature | 14–30 ngày | 7 ngày |
| archived | > 30 ngày | 30 ngày |

**Comment Count Gate:** Video mới (< 3 ngày) thường ít comment — không crawl để tiết kiệm proxy bandwidth.

---

## Thông tin bảo mật

| Biến | Mục đích |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 — chỉ dùng cho Mode 2 search.list và channels.list |
| `GCS_BUCKET_NAME` | Upload JSON thô |
| `GCP_PROJECT_ID` | BigQuery project |
| `BQ_DATASET` | BigQuery dataset (`sentiment_platform`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account |
| `BRIGHTDATA_PROXY_HOST/PORT/USERNAME/PASSWORD` | Proxy cho comment downloader |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng cho |
|---|---|---|
| `yt-dlp` | 2024.12.23 | Mode 0 — lấy video list từ channel (0 quota) |
| `feedparser` | 6.0.11 | Mode 1 — RSS feed YouTube channel (0 quota) |
| `google-api-python-client` | (qua google-cloud) | Mode 2 — YouTube search.list |
| `youtube-comment-downloader` | 0.1.78 | Crawl comments (0 YouTube quota) |
| `google-cloud-storage` | 2.18.2 | Upload JSON lên GCS |
| `google-cloud-bigquery` | 3.27.0 | Đọc/ghi BigQuery repositories |
| `python-dotenv` | 1.0.1 | Load `.env` |
| `pyyaml` | 6.0.2 | Load `pipeline_config.yaml` |

---

## GCS Output Convention

```
gs://social-media-sentiment-raw/raw/videos/YYYY/MM/DD/videos_run_HHMMSS.json
gs://social-media-sentiment-raw/raw/comments/YYYY/MM/DD/comments_{video_id}_HHMMSS.json

```

Convention này là bắt buộc — BigQuery External Table (layer_1) dùng path này để partition.

---

## Lưu ý quan trọng

- File trong folder này chạy với **Python 3.13.12** — không import bất cứ thứ gì từ `airflow/`
- Mỗi script trong `extract/` có thể chạy thủ công để test: `python -m elt.extract.video_extractor`
- `seed_loader.py` chỉ chạy 1 lần khi setup, hoặc khi cần thêm kênh/keyword mới
- DAG trong `airflow/` sẽ gọi vào các script này — không ngược lại
