# CLAUDE.md — elt/extract/

## Mục tiêu

Thực hiện thu thập dữ liệu từ YouTube theo 3 phase tuần tự:
1. **Phase A — Daily:** tìm video mới từ 18 channels qua search.list, filter keyword, enrich, crawl comments
2. **Phase B — Historical:** scan toàn bộ video cũ từ kênh chưa scan qua yt-dlp, batch 50, interleaved comment crawl
3. **Phase C — Backlog:** recrawl comments theo Video Maturity Model (priority scoring)

Toàn bộ output được ghi xuống **GCS** dưới dạng JSON thô. **Không** ghi trực tiếp vào BigQuery.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `base_extractor.py` | `BaseExtractor` abstract class — định nghĩa interface bắt buộc |
| `video_extractor.py` | `VideoExtractor` class — triển khai `run_daily()` (Phase A) và `run_historical()` (Phase B) |
| `comment_extractor.py` | `CommentExtractor` class — `crawl_batch()`, `crawl_batch_with_retry()`, `run_backlog()` (Phase C) |
| `helpers/ytdlp_video_fetcher.py` | yt-dlp wrapper — fetch channel videos, filter keywords, enrich batch (ThreadPool), build DTOs |
| `helpers/youtube_api_client.py` | YouTube Data API wrapper — `search_channel_recent()` cho Phase A |
| `helpers/comment_downloader.py` | youtube-comment-downloader + BrightData proxy wrapper |
| `helpers/comment_worker.py` | `CommentWorker` class — xử lý crawl + save comment 1 video (GCS-first, BQ-second) |

**Đã bỏ:** `helpers/rss_feed_reader.py` — thay bằng search.list per channel

---

## Luồng hoạt động chi tiết

```
main.py run_full() — 2:00 AM UTC+7
│
├── video_extractor.run_daily(execution_date, dag_run_id, budget, comment_extractor)
│   │
│   ├── Step 1: search_channel_recent() × 18 channels
│   │   search.list(channelId=X, order="date",
│   │       publishedAfter=now-3days, maxResults=20)
│   │   → list[dict] raw per channel
│   │   → 18 × 100 = 1,800 quota units
│   │
│   ├── Step 2: filter_by_keywords(all_raw)
│   │   So title với keyword_config (129 keywords)
│   │   Match → giữ, không match → bỏ
│   │
│   ├── Step 3: dedupe
│   │   crawl_state_repo.get_all_video_ids() → skip video đã có
│   │
│   ├── Step 4: enrich_batch(new_videos, max_workers=8)
│   │   ThreadPoolExecutor → _enrich_video() per video (yt-dlp)
│   │   Lấy: like_count, comment_count, tags, timestamp, description
│   │
│   ├── Step 5: build_video_dtos → save
│   │   upload_to_gcs(dtos)            ← GCS first
│   │   bulk_upsert_crawl_state(dtos)  ← BQ second
│   │
│   └── Step 6: comment_extractor.crawl_batch_with_retry(dtos, max_retries=2)
│
├── video_extractor.run_historical(execution_date, dag_run_id, budget, comment_extractor)
│   │
│   ├── get_unscanned_channels(limit) → nếu rỗng: return
│   │
│   └── Per channel:
│       ├── fetch_channel_videos(channel_url) — yt-dlp extract_flat=True
│       ├── filter_by_keywords(raw)
│       ├── get_existing_video_ids(channel_id) → skip đã có
│       │
│       ├── Batch loop (50 videos/batch):
│       │   ├── enrich_batch(batch, max_workers=8)
│       │   ├── build_video_dtos(enriched, channel_id)
│       │   ├── upload_to_gcs(dtos)            ← GCS first
│       │   ├── bulk_upsert_crawl_state(dtos)  ← BQ second
│       │   └── comment_extractor.crawl_batch(dtos) → collect fails
│       │
│       ├── crawl_batch_with_retry(channel_fails, max_retries=2)
│       └── mark_historically_scanned(channel_id)
│
├── comment_extractor.run_backlog(dag_run_id)
│   ├── get_videos_to_crawl() — priority score ORDER BY
│   └── crawl_batch_with_retry(videos, max_retries=2)
│
└── quota_repo.upsert_daily_summary()
```

---

## 2-Mode Discovery — Quota Cost

| Mode | Phase | Phương thức | Quota cost | Tần suất |
|---|---|---|---|---|
| search.list per channel | Phase A | YouTube Data API | 100 units/channel, 1,800/ngày | Hằng ngày |
| yt-dlp flat scan | Phase B | yt-dlp extract_flat=True | 0 units | 1 lần/kênh |

Enrich (tất cả modes): yt-dlp `extract_flat=False` per video, 0 quota.

---

## Phase A — search.list per channel

```python
youtube_api_client.search_channel_recent(
    channel_id=channel_id,
    published_after=now - timedelta(days=3),
    max_results=20,
)
```

Trả về `list[dict]` chứa `video_id, channel_id, title, published_at`.
Không dùng keyword param server-side — filter keyword **local** bằng `filter_by_keywords()`.

Lý do filter local thay vì server-side:
- YouTube search fuzzy matching không kiểm soát (search "Samsung Galaxy S25" trả video về S24)
- Local matching dùng cùng logic `filter_by_keywords` đã có, chính xác hơn
- Tiết kiệm quota (1 call/channel thay vì 5 calls/channel)

---

## Phase B — Historical Scan (batch 50, resume-safe)

Chỉ chạy cho kênh có `is_historically_scanned = FALSE`.
Sau khi tất cả 18 kênh scan xong → Phase B skip mãi mãi.

Resume sau crash: `get_existing_video_ids(channel_id)` trả video đã save trong BQ → skip, chỉ enrich/save video còn lại.

Kênh lớn (5,000-10,000 video matched):
- enrich_batch 50 videos × 8 workers ≈ 25s/batch
- Tổng ~100-200 batches → ~45-90 phút/kênh
- Crash chỉ mất tối đa 1 batch (50 videos)

---

## Comment Crawl — Interleaved Batch

Sau mỗi batch video save xong, comment crawl cho batch đó luôn rồi mới chuyển sang batch tiếp.

```
Batch 1 (50 videos): enrich → save → comment crawl batch 1
Batch 2 (50 videos): enrich → save → comment crawl batch 2
...
Retry: collect tất cả failed → retry × 2 → mark_skipped
```

CommentWorker.process(video) flow:
1. Check maturity (< 3 ngày → skip)
2. Download comments (youtube-comment-downloader + proxy)
3. Upload GCS ← first
4. Update crawl_state BQ ← second
5. Exception → return False (push to retry list)

---

## Video Maturity Model + Priority Scoring

| Stage | Tuổi video | Crawl lại sau | Priority Score |
|---|---|---|---|
| new | < 3 ngày | Bỏ qua | 100 |
| growing | 3-14 ngày | 3 ngày | 50-80 |
| mature | 14-30 ngày | 7 ngày | 30 |
| archived | > 30 ngày | 30 ngày | 10 |

Priority score 80: video growing có comment_count tăng > 20% so với lần crawl trước.

`get_videos_to_crawl()` ORDER BY priority_score DESC, published_at DESC.

---

## Retry Logic

```
crawl_batch(videos) → (success_count, failed_list)
crawl_batch_with_retry(videos, max_retries=2):
    Lần 1: crawl_batch(videos) → failed_list
    Retry 1: crawl_batch(failed_list) → still_failed
    Retry 2: crawl_batch(still_failed) → remaining
    remaining → mark_video_skipped() cho từng video
    return stats dict
```

---

## Thông tin bảo mật

| Biến | Dùng trong | Mục đích |
|---|---|---|
| `YOUTUBE_API_KEY` | `youtube_api_client.py` | search.list Phase A |
| `BRIGHTDATA_PROXY_HOST` | `comment_downloader.py` | Proxy hostname |
| `BRIGHTDATA_PROXY_PORT` | `comment_downloader.py` | Proxy port |
| `BRIGHTDATA_USERNAME` | `comment_downloader.py` | Proxy auth |
| `BRIGHTDATA_PASSWORD` | `comment_downloader.py` | Proxy auth |
| `GCS_BUCKET_NAME` | cả 2 extractors | Upload destination |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng trong | Mục đích |
|---|---|---|---|
| `yt-dlp` | 2024.12.23 | `ytdlp_video_fetcher.py` | Phase B historical + enrich tất cả modes |
| `google-api-python-client` | (qua google-cloud) | `youtube_api_client.py` | Phase A search.list per channel |
| `youtube-comment-downloader` | 0.1.78 | `comment_downloader.py` | Crawl comments (0 quota) |
| `requests` | 2.32.3 | `comment_downloader.py` | HTTP qua BrightData proxy |
| `google-cloud-bigquery` | 3.27.0 | cả 2 extractors | Đọc/ghi crawl state |
| `google-cloud-storage` | 2.18.2 | cả 2 extractors | Upload JSON |

---

## Cách test thủ công

```bash
python -m elt.main --mode videos --date 2026-04-20
python -m elt.main --mode comments
python -m elt.main --mode full --date 2026-04-20
```

---

## Output GCS Convention (bắt buộc)

```
gs://social-media-sentiment-raw/raw/videos/YYYY/MM/DD/videos_run_HHMMSS.json
gs://social-media-sentiment-raw/raw/comments/YYYY/MM/DD/comments_{video_id}_HHMMSS.json
```

BigQuery External Table (layer_1_raw) partition theo path này — **không được thay đổi format**.