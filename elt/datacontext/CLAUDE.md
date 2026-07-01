# CLAUDE.md — elt/datacontext/

## Mục tiêu

Cung cấp lớp trừu tượng kết nối với hạ tầng lưu trữ (GCS) và định nghĩa cấu trúc dữ liệu (DTOs) dùng chung trong toàn bộ ELT pipeline.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `gcs_client.py` | `GCSClient` class — wrap `google-cloud-storage`. Cung cấp `upload_json()`, `file_exists()`, `list_files()`, `build_videos_path()`, `build_comments_path()`. Tất cả I/O với GCS đi qua đây |
| `models/video_dto.py` | `VideoDTO` dataclass — schema dữ liệu video trước khi ghi xuống GCS |
| `models/comment_dto.py` | `CommentDTO` dataclass — schema dữ liệu comment trước khi ghi xuống GCS |
| `models/channel_dto.py` | `ChannelDTO` dataclass — schema dữ liệu kênh dùng trong seed và repository |
| `models/keyword_dto.py` | `KeywordDTO` dataclass — schema keyword (keyword_id, keyword_text, search_cluster) |

---

## Luồng hoạt động

```
extract/video_extractor.py
    │ tạo VideoDTO (qua ytdlp_video_fetcher.build_video_dtos)
    ▼
models/video_dto.py → .to_dict() → serialize to list[dict]
    │
    ▼
gcs_client.py → upload_json() → GCS bucket
    path: raw/videos/YYYY/MM/DD/videos_run_HHMMSS.json
```

```
extract/helpers/comment_worker.py
    │ tạo CommentDTO list (qua comment_downloader.to_comment_dtos)
    ▼
models/comment_dto.py → .to_dict() → serialize to list[dict]
    │
    ▼
gcs_client.py → upload_json() → GCS bucket
    path: raw/comments/YYYY/MM/DD/comments_{video_id}_HHMMSS.json
```

---

## Thông tin bảo mật

- `GCS_BUCKET_NAME` — đọc từ `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` — đọc từ `.env`, GCSClient tự load qua `google-auth`

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng cho |
|---|---|---|
| `google-cloud-storage` | 2.18.2 | Upload / kiểm tra file trên GCS |
| `google-auth` | 2.37.0 | Xác thực GCP service account |
| `python-dotenv` | 1.0.1 | Load biến môi trường |

---

## Output format — JSON mẫu cho GCS

### 1. Video (file: `raw/videos/2026/04/20/videos_run_020500.json`)

```json
[
  {
    "video_id": "abc123xyz",
    "channel_id": "UCvZ_9N7JRRb-tM_qh9Bx1ew",
    "title": "Review Samsung Galaxy S25 Ultra",
    "description": "Đánh giá chi tiết...",
    "view_count": 150000,
    "like_count": 5000,
    "comment_count": 1200,
    "duration_seconds": 650,
    "tags": ["samsung", "review", "s25 ultra"],
    "thumbnail_url": "https://i.ytimg.com/vi/abc/maxresdefault.jpg",
    "published_at": "2026-04-18T08:00:00Z",
    "search_mode": "DAILY",
    "keyword_matched": "Samsung Galaxy S25",
    "crawled_at": "2026-04-20T02:05:00Z"
  }
]
```

### 2. Comment (file: `raw/comments/2026/04/20/comments_abc123xyz_020800.json`)

```json
[
  {
    "comment_id": "UgwBx1234",
    "video_id": "abc123xyz",
    "channel_id": "UCvZ_9N7JRRb-tM_qh9Bx1ew",
    "author": "Nguyen Van A",
    "text": "Pin trâu ghê, dùng 2 ngày mới hết",
    "like_count": 15,
    "published_at": "2026-04-18T10:30:00Z",
    "is_reply": false,
    "parent_comment_id": null,
    "crawled_at": "2026-04-20T02:08:00Z"
  }
]
```

---

## Lưu ý

- VideoDTO field `search_mode`: giá trị là `"DAILY"` (Phase A), `"MODE0"` (Phase B historical)
- GCS path convention là bắt buộc — BigQuery External Table partition theo path
- `GCSClient` thread-safe — có thể dùng từ nhiều thread trong enrich_batch