# CLAUDE.md — tests/

## Mục tiêu

Kiểm thử tự động từng layer của pipeline để đảm bảo tính đúng đắn trước khi tích hợp vào Airflow DAG. Mỗi sub-folder test tương ứng với 1 folder chính trong dự án.

---

## Chức năng và nhiệm vụ từng folder

| Folder | Nhiệm vụ |
|---|---|
| `test_elt/` | Test extract logic, GCS upload, repository queries, quota budget |
| `test_transform/` | Test dbt model output, data quality checks, schema validation |
| `test_nlp/` | Test annotation format, inference output, confidence routing logic |

---

## Test files cho elt/extract

| Test file | File được test | Focus |
|---|---|---|
| `test_ytdlp_video_fetcher.py` | `ytdlp_video_fetcher.py` | fetch_channel_videos, filter_by_keywords, enrich_batch, build_video_dtos |
| `test_youtube_api_client.py` | `youtube_api_client.py` | search_channel_recent, get_video_details |
| `test_comment_downloader.py` | `comment_downloader.py` | download, to_comment_dtos, proxy config |
| `test_comment_worker.py` | `comment_worker.py` | process (GCS-first/BQ-second), maturity skip, retry return False |
| `test_video_extractor.py` | `video_extractor.py` | run_daily (Phase A), run_historical (Phase B batch loop, resume) |
| `test_comment_extractor.py` | `comment_extractor.py` | crawl_batch, crawl_batch_with_retry, run_backlog (Phase C) |

Đã bỏ: `test_rss_feed_reader.py`

---

## Luồng hoạt động

```bash
pytest tests/test_elt/        <- chạy sau khi code elt/ xong
pytest tests/test_transform/  <- chạy sau khi dbt models xong
pytest tests/test_nlp/        <- chạy sau khi inference pipeline xong

pytest tests/                 <- chạy toàn bộ
```

---

## Công nghệ và thư viện

| Thư viện | Version | Mục đích |
|---|---|---|
| `pytest` | 8.3.4 | Test framework |
| `unittest.mock` | stdlib | Mock BigQuery, GCS, API calls |

---

## Quy tắc

- Test file đặt tên `test_*.py`
- Mock toàn bộ external calls (BigQuery, GCS, YouTube API, yt-dlp, Gemini) — không gọi API thật trong test
- Mỗi repository method có ít nhất 1 unit test
- Không để test làm thay đổi dữ liệu production trên BQ
- Test enrich_batch: mock _enrich_video, verify ThreadPoolExecutor được gọi với max_workers đúng
- Test crawl_batch_with_retry: mock worker.process return False → verify retry logic + mark_skipped
- Test run_historical: mock get_existing_video_ids → verify skip đúng video đã có (resume)
- Test GCS-first principle: verify upload_to_gcs được gọi trước bulk_upsert