# CLAUDE.md — elt/extract/

## Mục tiêu

Thực hiện thu thập dữ liệu từ YouTube theo 2 bước tuần tự:
1. **Crawl danh sách video** (video_extractor.py) — tìm video phù hợp keyword
2. **Crawl comments của video** (comment_extractor.py) — lấy bình luận từ video đã tìm thấy

Toàn bộ output được ghi xuống **GCS** dưới dạng JSON thô. **Không** ghi trực tiếp vào BigQuery.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `base_extractor.py` | `BaseExtractor` abstract class — định nghĩa interface bắt buộc cho cả video và comment extraction |
| `video_extractor.py` | `VideoExtractor` class — triển khai 3-mode video discovery theo quota budget |
| `comment_extractor.py` | `CommentExtractor` class — crawl comments qua youtube-comment-downloader + BrightData proxy (0 YouTube API quota) |

---

## Luồng hoạt động

```
[Ngày mới bắt đầu]
        │
        ▼
video_extractor.py
        │
        ├── Đọc channel_config từ BQ (channel_repository)
        ├── Đọc keyword_config từ BQ
        ├── Kiểm tra quota còn lại (quota_budget)
        │
        ├── MODE 0 — Historical Scan (yt-dlp, 0 API quota)
        │   └── Kênh chưa scan lịch sử → get_unscanned_channels()
        │       yt-dlp lấy toàn bộ video cũ của kênh matching keyword
        │       → mark_historically_scanned() sau khi xong
        │
        ├── MODE 1 — RSS Daily (feedparser, 0 API quota)
        │   └── 26 kênh × RSS feed → 15 video mới nhất/kênh
        │       Pre-filter: title có chứa keyword không?
        │
        └── MODE 2 — Keyword Sweep (search.list, 100 units/call)
            └── ~15 cluster keywords → search global
                Tiêu thụ từ bucket_search
                │
                ▼
        [video_id list] → ghi vào video_crawl_state (BQ)
                │
                ▼
comment_extractor.py
        │
        ├── Đọc video cần crawl từ video_crawl_state (theo Video Maturity Model)
        ├── Comment Count Gate: bỏ qua video < 3 ngày tuổi
        │
        └── Với mỗi video đủ điều kiện:
            youtube-comment-downloader qua BrightData proxy
            → CommentDTO list (tối đa 500 comments/video)
            → serialize to JSON
            → gcs_client.upload()
            → GCS: raw/youtube/YYYY/MM/DD/keyword_HHMMSS.json
            → cập nhật video_crawl_state
```

---

## 3-Mode Discovery — Quota Cost

| Mode | Phương thức | Quota cost | Tần suất |
|---|---|---|---|
| 0 — Historical Scan | yt-dlp | 0 units | 1 lần/kênh |
| 1 — RSS Daily | feedparser | 0 units | Hằng ngày |
| 2 — Keyword Sweep | search.list | 100 units/call | Hằng ngày |

---

## Mode 2 — Chi tiết logic tìm kiếm

Mode 2 phân loại keyword thành 2 loại dựa trên dữ liệu sẵn có trong BQ, không cần thêm field mới vào schema:

```
keyword_text_set = SET(tất cả keyword_text trong keyword_config)

Group keyword_config by search_cluster:
    search_cluster IN keyword_text_set?

    CÓ  → Specific product cluster
          search_cluster = tên model gốc = chính xác 1 keyword_text
          → search(q=search_cluster): 1 call / cluster
          VD: cluster "Samsung Galaxy S25" thay vì 5 calls cho 5 variants

    KHÔNG → Comparison / category cluster
            cluster là nhãn tổng hợp, không phải keyword thật
            → search(q=keyword_text): 1 call / keyword
            VD: cluster "Điện thoại tầm 5 triệu" → 3 calls cho 3 keywords
```

Điều kiện tiên quyết bắt buộc: seed_loader.py phải đảm bảo cluster name
của specific product = chính xác 1 keyword_text trong BQ. Logic detect
trong video_extractor phụ thuộc hoàn toàn vào quy ước này.

---

## Phân tích quota Mode 2 — 26 kênh, 100 keywords

Giả sử 75 specific + 25 comparison:

```
Specific:   75 keywords → ~15 clusters × 1 call   = 1,500 units
Comparison: 25 keywords × 1 call                   = 2,500 units
videos.list enrich metadata (batch 50)             =    ~40 units
Total Mode 2 / ngày:                               ~4,040 units
Còn lại trong bucket_search (9,000):               ~4,960 units
```
**Tổng quota search tối đa/ngày:** Mode 2 với ~4,040 units. Phần còn lại của bucket_search ~4,960 units dành cho Mode 0 historical scan.

| Tỉ lệ specific/comparison | Clusters | Comparison calls | Tổng units | Còn lại |
|---|---|---|---|---|
| 90/10 | ~18 | 10 | 2,800 | 6,160 |
| 75/25 (dự tính) | ~15 | 25 | 4,040 | 4,960 |
| 60/40 | ~12 | 40 | 5,240 | 3,760 |
| 50/50 | ~10 | 50 | 6,040 | 2,960 |

---

## Thông tin bảo mật

| Biến | Dùng trong | Mục đích |
|---|---|---|
| `YOUTUBE_API_KEY` | `video_extractor.py` | YouTube search.list (Mode 2) |
| `BRIGHTDATA_PROXY_HOST` | `comment_extractor.py` | Proxy hostname |
| `BRIGHTDATA_PROXY_PORT` | `comment_extractor.py` | Proxy port |
| `BRIGHTDATA_USERNAME` | `comment_extractor.py` | Proxy auth |
| `BRIGHTDATA_PASSWORD` | `comment_extractor.py` | Proxy auth |
| `GCS_BUCKET_NAME` | cả 2 extractors | Upload destination |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng trong | Mục đích |
|---|---|---|---|
| `yt-dlp` | 2024.12.23 | `video_extractor.py` | Mode 0 — lấy video metadata từ channel |
| `feedparser` | 6.0.11 | `video_extractor.py` | Mode 1 — RSS feed |
| `youtube-comment-downloader` | 0.1.78 | `comment_extractor.py` | Crawl comments (0 quota) |
| `requests` | 2.32.3 | `comment_extractor.py` | HTTP qua BrightData proxy |
| `google-cloud-bigquery` | 3.27.0 | cả 2 | Đọc/ghi crawl state |
| `google-cloud-storage` | 2.18.2 | cả 2 | Upload JSON |

---

## Cách test thủ công

```bash
# Test video extractor (Mode 1 RSS, 0 quota)
python -m elt.extract.video_extractor --mode rss --channel UC_example

# Test comment extractor (1 video)
python -m elt.extract.comment_extractor --video_id dQw4w9WgXcQ
```

---

## Output GCS Convention (bắt buộc)

```
gs://social-media-sentiment-raw/raw/youtube/YYYY/MM/DD/keyword_HHMMSS.json
```

BigQuery External Table (layer_1_raw) partition theo path này — **không được thay đổi format**.
