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
| `main.py` | Entry point — orchestrate 3 phases: Phase A (daily) → Phase B (historical) → Phase C (backlog) |
| `datacontext/gcs_client.py` | `GCSClient` class — kết nối GCS, upload JSON, kiểm tra file tồn tại. Mọi I/O với GCS đều đi qua đây |
| `datacontext/models/video_dto.py` | `VideoDTO` dataclass — cấu trúc dữ liệu video |
| `datacontext/models/comment_dto.py` | `CommentDTO` dataclass — cấu trúc dữ liệu comment |
| `datacontext/models/channel_dto.py` | `ChannelDTO` dataclass — cấu trúc dữ liệu kênh |
| `datacontext/models/keyword_dto.py` | `KeywordDTO` dataclass — cấu trúc dữ liệu keyword |
| `seed_data/seed_loader.py` | Script chạy thủ công — đọc 2 file CSV và load vào BQ tables `channel_config` + `keyword_config` |
| `extract/base_extractor.py` | `BaseExtractor` abstract class — định nghĩa interface chuẩn |
| `extract/video_extractor.py` | `VideoExtractor` class — triển khai Phase A (search.list per channel) và Phase B (yt-dlp historical) |
| `extract/comment_extractor.py` | `CommentExtractor` class — crawl comments với `crawl_batch`, `crawl_batch_with_retry`, `run_backlog` |
| `extract/helpers/ytdlp_video_fetcher.py` | yt-dlp wrapper — `fetch_channel_videos` (flat), `filter_by_keywords`, `enrich_batch` (ThreadPool), `build_video_dtos` |
| `extract/helpers/youtube_api_client.py` | YouTube Data API wrapper — `search_channel_recent` (search.list per channel) |
| `extract/helpers/comment_downloader.py` | youtube-comment-downloader + BrightData proxy wrapper |
| `extract/helpers/comment_worker.py` | `CommentWorker` class — xử lý crawl + save comment cho 1 video (GCS-first, BQ-second) |
| `repositories/channel_repository.py` | `ChannelRepository` — CRUD BigQuery table `channel_config` |
| `repositories/crawl_state_repository.py` | `CrawlStateRepository` — quản lý `video_crawl_state`: video nào đã crawl, cần crawl lại |
| `repositories/keyword_repository.py` | `KeywordRepository` — đọc danh sách keywords |
| `repositories/quota_repository.py` | `QuotaRepository` — ghi log quota API đã dùng |

**Đã bỏ:** `extract/helpers/rss_feed_reader.py` — RSS không ổn định (404/500), thay bằng search.list per channel

---

## Luồng hoạt động — 3-Phase Pipeline

```
main.py run_full() — chạy 2:00 AM UTC+7 hằng ngày
│
│  ══════ PHASE A — DAILY (ưu tiên cao, ~20-30 phút) ══════
│
├─ search.list per channel (18 channels × 100 units = 1,800 units)
│   publishedAfter = now - 3 days, order = date, maxResults = 20
├─ filter keyword local (so title với keyword_config)
├─ dedupe: skip video đã có trong video_crawl_state
├─ enrich yt-dlp (ThreadPool 8 workers, 0 quota)
├─ save: GCS first → BQ second
├─ comment crawl: crawl_batch_with_retry(dtos, max_retries=2)
│
│  ══════ PHASE B — HISTORICAL (chỉ chạy khi có kênh chưa scan) ══════
│
├─ get_unscanned_channels() → nếu rỗng: skip Phase B
├─ Per channel:
│   ├─ yt-dlp fetch_channel_videos (extract_flat=True, 1 request)
│   ├─ filter_by_keywords (local)
│   ├─ get_existing_video_ids(channel_id) → skip đã có (resume)
│   ├─ Batch loop (50 videos/batch):
│   │   ├─ enrich_batch (ThreadPool 8 workers)
│   │   ├─ build_video_dtos
│   │   ├─ save: GCS first → BQ second
│   │   └─ comment crawl batch (interleaved)
│   ├─ Retry failed comments × 2 → mark_skipped
│   └─ mark_historically_scanned(channel_id)
│
│  ══════ PHASE C — BACKLOG (recrawl theo maturity) ══════
│
├─ get_videos_to_crawl() — priority score ORDER BY
├─ crawl_batch_with_retry(videos, max_retries=2)
└─ quota_repo.upsert_daily_summary()
```

---

## Video Maturity Model

| Stage | Tuổi video | Crawl lại sau | Priority Score |
|---|---|---|---|
| new | < 3 ngày | Bỏ qua (Comment Count Gate) | 100 |
| growing | 3-14 ngày | 3 ngày | 50-80 (80 nếu comment tăng > 20%) |
| mature | 14-30 ngày | 7 ngày | 30 |
| archived | > 30 ngày | 30 ngày | 10 |

---

## Data Integrity

Nguyên tắc **GCS-first, BQ-second** áp dụng ở mọi save point:

```python
try:
    self._upload_to_gcs(data, execution_date)
    self._save_to_crawl_state(data)
except Exception as e:
    logger.error("Lỗi khi lưu trữ dữ liệu: %s", e)
    raise
```

Phase B: crash ở batch 30/90 → restart → `get_existing_video_ids` skip 1,500 đã save → enrich từ batch 31.

---

## Thông tin bảo mật

| Biến | Dùng trong | Mục đích |
|---|---|---|
| `YOUTUBE_API_KEY` | `youtube_api_client.py` | search.list Phase A |
| `BRIGHTDATA_PROXY_HOST/PORT/USERNAME/PASSWORD` | `comment_downloader.py` | Proxy cho comment crawl |
| `GCS_BUCKET_NAME` | `gcs_client.py` | Upload destination |
| `GCP_PROJECT_ID` + `BQ_DATASET` | repositories | BigQuery project/dataset |
| `GOOGLE_APPLICATION_CREDENTIALS` | tất cả GCP clients | Service account |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng trong | Mục đích |
|---|---|---|---|
| `yt-dlp` | 2024.12.23 | `ytdlp_video_fetcher.py` | Phase B historical scan + enrich (tất cả modes) |
| `google-api-python-client` | (qua google-cloud) | `youtube_api_client.py` | Phase A search.list per channel |
| `youtube-comment-downloader` | 0.1.78 | `comment_downloader.py` | Crawl comments (0 YouTube quota) |
| `requests` | 2.32.3 | `comment_downloader.py` | HTTP qua BrightData proxy |
| `google-cloud-bigquery` | 3.27.0 | repositories | Đọc/ghi BigQuery |
| `google-cloud-storage` | 2.18.2 | `gcs_client.py` | Upload JSON lên GCS |
| `python-dotenv` | 1.0.1 | `config.py` | Load `.env` |
| `pyyaml` | 6.0.2 | `config.py` | Load `pipeline_config.yaml` |

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
- Mỗi script trong `extract/` có thể chạy thủ công để test: `python -m elt.main --mode full`
- `seed_loader.py` chỉ chạy 1 lần khi setup, hoặc khi cần thêm kênh/keyword mới
- DAG trong `airflow/` sẽ gọi vào các script này — không ngược lại