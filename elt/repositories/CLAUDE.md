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

Bucket: `social-media-sentiment-raw`

| Loại data | GCS prefix | Ví dụ đường dẫn đầy đủ |
|---|---|---|
| Video metadata | `raw/videos/YYYY/MM/DD/` | `raw/videos/2026/03/15/videos_run_020500.json` |
| Comments | `raw/comments/YYYY/MM/DD/` | `raw/comments/2026/03/15/comments_dQw4w9WgXcQ_020500.json` |

BigQuery External Table trỏ vào:
- T06 `raw_videos` → `gs://social-media-sentiment-raw/raw/videos/*`
- T07 `raw_comments` → `gs://social-media-sentiment-raw/raw/comments/*`

`GCSClient.build_videos_path()` và `build_comments_path()` đã implement đúng convention này.

---

## Luồng hoạt động

```
elt/quota_budget.py
    └── quota_repository.get_today_used_by_bucket(today)
            → dict[str, int] {"search_videos": N, "channel_seed": N}
            → QuotaBudget.from_config(config, already_used)

elt/extract/video_extractor.py
    ├── channel_repository.get_active_channels()         ← Phase A: 18 channels cho search.list
    ├── channel_repository.get_unscanned_channels(limit)  ← Phase B: kênh chưa scan
    ├── channel_repository.mark_historically_scanned(id)  ← Phase B: sau khi scan xong
    ├── keyword_repository.get_active_keywords()          ← Filter keyword local
    ├── crawl_state_repository.get_all_video_ids()        ← Phase A dedupe
    ├── crawl_state_repository.get_existing_video_ids(ch) ← Phase B resume
    ├── crawl_state_repository.bulk_upsert_from_video_dtos(videos)
    └── quota_repository.log_operation(...)

elt/extract/comment_extractor.py
    ├── crawl_state_repository.get_videos_to_crawl()      ← Phase C backlog (priority scoring)
    ├── crawl_state_repository.update_after_comment_crawl(...)
    ├── crawl_state_repository.mark_video_skipped(video_id)
    └── quota_repository.log_operation(...)

elt/extract/helpers/comment_worker.py
    ├── crawl_state_repository.update_after_comment_crawl(...)
    ├── crawl_state_repository.mark_video_skipped(video_id)
    └── gcs_client.upload_json(...)

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

Caller dùng output để filter keyword local trong Phase A và Phase B: `filter_by_keywords()` so title/description với `keyword_text`.

### CrawlStateRepository

| Method | Signature | Ghi chú |
|---|---|---|
| `bulk_upsert_from_video_dtos` | `(videos: list[VideoDTO]) -> None` | MERGE qua tmp table. NOT MATCHED → INSERT `crawl_status='pending'`. MATCHED → UPDATE comment_count, maturity_stage |
| `get_all_video_ids` | `() -> set[str]` | SELECT video_id FROM video_crawl_state. Dùng cho Phase A dedupe |
| `get_existing_video_ids` | `(channel_id: str) -> set[str]` | SELECT video_id WHERE channel_id = @id. Dùng cho Phase B resume sau crash |
| `get_videos_to_crawl` | `() -> list[dict]` | Tính eligibility theo Video Maturity Model. ORDER BY priority_score DESC, published_at DESC |
| `update_after_comment_crawl` | `(video_id, comments_crawled_this_run, crawled_at, max_comments_per_video) -> None` | UPDATE total_comments_crawled += delta, recompute is_comment_complete, maturity_stage |
| `mark_video_skipped` | `(video_id: str) -> None` | SET crawl_status = 'skipped' |

### Priority Scoring trong get_videos_to_crawl

```sql
ORDER BY
    CASE
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 3
            THEN 100
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 14
             AND comment_count > COALESCE(last_comment_count, 0) * 1.2
            THEN 80
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 14
            THEN 50
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), published_at, DAY) < 30
            THEN 30
        ELSE 10
    END DESC,
    published_at DESC
```