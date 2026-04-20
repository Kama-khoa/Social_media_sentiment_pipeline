# CLAUDE.md — elt/repositories/

## Mục tiêu

Lớp Data Access — tất cả thao tác đọc/ghi BigQuery trong ELT pipeline đều đi qua đây. Các extractor và pipeline không được gọi BigQuery trực tiếp.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ | BQ Tables |
|---|---|---|
| `quota_repository.py` | `QuotaRepository` — ghi log và tổng hợp quota API đã dùng | `quota_operation_log`, `quota_daily_summary` |
| `channel_repository.py` | `ChannelRepository` — quản lý danh sách kênh YouTube | `channel_config` |
| `keyword_repository.py` | `KeywordRepository` — đọc danh sách keywords cho video discovery | `keyword_config` |
| `crawl_state_repository.py` | `CrawlStateRepository` — theo dõi trạng thái crawl từng video | `video_crawl_state` |

---

## GCS Path Convention (chính thức)

Bucket: `product-sentiment-raw-1806`

| Loại data | GCS prefix | Ví dụ đường dẫn đầy đủ |
|---|---|---|
| Video metadata | `raw/videos/YYYY/MM/DD/` | `raw/videos/2026/03/15/videos_run_020500.json` |
| Comments | `raw/comments/YYYY/MM/DD/` | `raw/comments/2026/03/15/comments_dQw4w9WgXcQ_020500.json` |

BigQuery External Table trỏ vào:
- T06 `raw_videos` → `gs://product-sentiment-raw-1806/raw/videos/*`
- T07 `raw_comments` → `gs://product-sentiment-raw-1806/raw/comments/*`

`GCSClient.build_videos_path()` và `build_comments_path()` đã implement đúng convention này.

---

## Luồng hoạt động

```
elt/quota_budget.py
    │
    └── quota_repository.get_today_used_by_bucket(today)
            → dict[str, int] {"search_videos": N, "channel_seed": N}
            → QuotaBudget.from_config(config, already_used)

elt/extract/video_extractor.py
    │
    ├── channel_repository.get_active_channels()
    ├── channel_repository.get_unscanned_channels(limit)
    ├── channel_repository.mark_historically_scanned(channel_id)
    │
    ├── keyword_repository.get_active_keywords()
    │       → list[KeywordDTO]
    │       → VideoExtractor build Mode1 filter + Mode2 search queries
    │
    ├── crawl_state_repository.bulk_upsert_from_video_dtos(videos)
    │
    └── quota_repository.log_operation(...)

elt/extract/comment_extractor.py
    │
    ├── crawl_state_repository.get_videos_to_crawl()
    ├── crawl_state_repository.update_after_comment_crawl(...)
    ├── crawl_state_repository.mark_video_skipped(video_id)
    └── quota_repository.log_operation(...)  ← ghi comments_collected

[Cuối DAG]
    └── quota_repository.upsert_daily_summary(today, dag_run_id)
```

---

## Key Methods

### QuotaRepository

| Method | Signature | Ghi chú |
|---|---|---|
| `log_operation` | `(operation_type, bucket, units_used, dag_run_id, videos_processed=0, comments_collected=0, execution_time_seconds=None) -> None` | INSERT 1 row. `bucket` phải là `QuotaBucket.value` ("search_videos" hoặc "channel_seed") |
| `get_today_used_by_bucket` | `(today: date) -> dict[str, int]` | GROUP BY bucket, trả về dict tương thích với `QuotaBudget.from_config()` |
| `upsert_daily_summary` | `(today: date, dag_run_id: str) -> None` | MERGE aggregate từ `quota_operation_log`. Chạy 1 lần cuối DAG |

### ChannelRepository

| Method | Signature | Ghi chú |
|---|---|---|
| `get_active_channels` | `() -> list[ChannelDTO]` | WHERE is_active = TRUE, ORDER BY subscriber_count DESC |
| `get_unscanned_channels` | `(limit: int = 5) -> list[ChannelDTO]` | WHERE is_historically_scanned = FALSE, ORDER BY subscriber_count DESC |
| `mark_historically_scanned` | `(channel_id: str) -> None` | UPDATE is_historically_scanned = TRUE, historical_scan_completed_at = NOW |

### KeywordRepository

| Method | Signature | Ghi chú |
|---|---|---|
| `get_active_keywords` | `() -> list[KeywordDTO]` | WHERE is_active = TRUE. Trả `KeywordDTO(keyword_id, keyword_text, search_cluster)` |

Caller dùng output để build 2 structures trong VideoExtractor:
- `keyword_text_set = {kw.keyword_text for kw in keywords}` → detect specific vs comparison cluster trong Mode 2
- `groupby(keywords, key=lambda kw: kw.search_cluster)` → build search call list cho Mode 2

### CrawlStateRepository

| Method | Signature | Ghi chú |
|---|---|---|
| `bulk_upsert_from_video_dtos` | `(videos: list[VideoDTO]) -> None` | MERGE qua tmp table (load job, synchronous). NOT MATCHED → INSERT với `crawl_status='pending'`. MATCHED → UPDATE chỉ comment_count, maturity_stage |
| `get_videos_to_crawl` | `() -> list[dict]` | Tự tính eligibility theo Video Maturity Model. Không nhận tham số. ORDER BY maturity_stage ưu tiên 'new' trước |
| `update_after_comment_crawl` | `(video_id, comments_crawled_this_run, crawled_at, max_comments_per_video) -> None` | UPDATE `total_comments_crawled += delta`, recompute `is_comment_complete`, `maturity_stage` |
| `mark_video_skipped` | `(video_id: str) -> None` | SET crawl_status = 'skipped'. Dùng khi Comment Count Gate quyết định bỏ qua |

---

## Video Maturity Model — Re-crawl eligibility logic

`get_videos_to_crawl()` dùng SQL sau để tự tính eligibility (không nhận tham số từ caller):

```sql
WHERE crawl_status != 'skipped'
  AND is_comment_complete = FALSE
  AND (
      last_comment_crawled_at IS NULL                          -- Chưa bao giờ cào
      OR (
          TIMESTAMP_DIFF(NOW(), published_at, DAY) < 3
          AND TIMESTAMP_DIFF(NOW(), last_comment_crawled_at, HOUR) >= 24   -- new: mỗi 24h
      )
      OR (
          TIMESTAMP_DIFF(NOW(), published_at, DAY) BETWEEN 3 AND 14
          AND TIMESTAMP_DIFF(NOW(), last_comment_crawled_at, DAY) >= 3     -- growing: mỗi 3 ngày
      )
      OR (
          TIMESTAMP_DIFF(NOW(), published_at, DAY) BETWEEN 14 AND 30
          AND TIMESTAMP_DIFF(NOW(), last_comment_crawled_at, DAY) >= 7     -- mature: mỗi 7 ngày
      )
      OR (
          TIMESTAMP_DIFF(NOW(), published_at, DAY) > 30
          AND TIMESTAMP_DIFF(NOW(), last_comment_crawled_at, DAY) >= 30    -- archived: mỗi 30 ngày
      )
  )
ORDER BY CASE maturity_stage WHEN 'new' THEN 1 WHEN 'growing' THEN 2
                             WHEN 'mature' THEN 3 WHEN 'archived' THEN 4 END
```

---

## Dependency với VideoDTO

`CrawlStateRepository.bulk_upsert_from_video_dtos()` đọc các fields sau từ `VideoDTO`:

| VideoDTO field | BQ column | Ghi chú |
|---|---|---|
| `video_id` | `video_id` PK | |
| `channel_id` | `channel_id` FK | |
| `keyword_matched` | → JOIN `keyword_config` | Repository tự JOIN để lấy `keyword_id` trong MERGE SQL |
| `search_mode` | `search_mode` | MODE0 / MODE1 / MODE2 |
| `published_at` | `published_at` | Dùng để tính maturity_stage |
| `comment_count` | `comment_count` | Snapshot tại thời điểm discover |

---

## Thứ tự bucket values (critical)

`QuotaBudget.from_config()` gọi `already_used_by_bucket.get(bucket.value, 0)` với:
- `QuotaBucket.SEARCH.value = "search_videos"`
- `QuotaBucket.CHANNEL_SEED.value = "channel_seed"`

Field `bucket` trong `quota_operation_log` **phải lưu đúng** các giá trị này — không phải "SEARCH"/"CHANNEL_SEED".

---

## Thông tin bảo mật

- `GCP_PROJECT_ID`, `BQ_DATASET`, `GOOGLE_APPLICATION_CREDENTIALS` — đọc từ `.env`, truyền qua constructor
- Không log API key hay credentials trong `quota_operation_log`

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng cho |
|---|---|---|
| `google-cloud-bigquery` | 3.27.0 | Toàn bộ BigQuery operations |
| `db-dtypes` | 1.3.1 | Xử lý kiểu dữ liệu BQ (DATE, TIMESTAMP) |
| `python-dotenv` | 1.0.1 | Load `.env` |

---

## Lưu ý

- Mọi query đều dùng **parameterized queries** (`bigquery.ScalarQueryParameter`) — không bao giờ string format SQL trực tiếp
- Mỗi repository nhận `bigquery.Client` qua constructor (dependency injection) để dễ test mock
- `quota_operation_log` ghi theo từng API operation riêng lẻ — `quota_daily_summary` tổng hợp cuối DAG
- `bulk_upsert_from_video_dtos` dùng load job (không phải streaming insert) để đảm bảo tmp table sẵn sàng đồng bộ trước khi MERGE
- Tmp table được xóa ngay sau MERGE thành công (`delete_table(not_found_ok=True)`)