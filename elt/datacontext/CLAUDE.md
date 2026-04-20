# CLAUDE.md — elt/datacontext/

## Mục tiêu

Cung cấp lớp trừu tượng kết nối với hạ tầng lưu trữ (GCS) và định nghĩa cấu trúc dữ liệu (DTOs) dùng chung trong toàn bộ ELT pipeline.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `gcs_client.py` | `GCSClient` class — wrap `google-cloud-storage`. Cung cấp `upload_json()`, `file_exists()`, `list_files()`. Tất cả I/O với GCS đi qua đây |
| `models/video_dto.py` | `VideoDTO` dataclass — schema dữ liệu video trước khi ghi xuống GCS |
| `models/comment_dto.py` | `CommentDTO` dataclass — schema dữ liệu comment trước khi ghi xuống GCS |
| `models/channel_dto.py` | `ChannelDTO` dataclass — schema dữ liệu kênh dùng trong seed và repository |

---

## Luồng hoạt động

```
extract/video_extractor.py
    │ tạo VideoDTO
    ▼
models/video_dto.py → serialize to dict
    │
    ▼
gcs_client.py → upload_json() → GCS bucket
```

```
extract/comment_extractor.py
    │ tạo CommentDTO list
    ▼
models/comment_dto.py → serialize to list[dict]
    │
    ▼
gcs_client.py → upload_json() → GCS bucket
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

## Output format (JSON/JSONL mẫu cho GCS)
Để tối ưu cho BigQuery External Tables và luồng cào dữ liệu bất đồng bộ, dữ liệu Video và Comment được lưu thành 2 loại file hoàn toàn tách biệt trên GCS.

### 1. Dữ liệu Video (Ví dụ file: `raw/videos/2026/04/09/videos_run_143000.json`)
List các `VideoDTO` được cào trong một batch.

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
    "thumbnail_url": "[https://i.ytimg.com/vi/abc/maxresdefault.jpg](https://i.ytimg.com/vi/abc/maxresdefault.jpg)",
    "published_at": "2026-04-05T08:00:00Z",
    "search_mode": "MODE1",
    "keyword_matched": "đánh giá samsung s25",
    "crawled_at": "2026-04-09T07:30:00Z"
  }
]
```

### 2. Dữ liệu Comment (Ví dụ file: `raw/comments/2026/04/09/comments_abc123xyz_143500.json`)
List các CommentDTO thuộc về MỘT video cụ thể (File được tạo ra sau khi youtube-comment-downloader chạy xong cho video đó). Bắt buộc phải có video_id làm Foreign Key.

```json
[
  {
    "comment_id": "UgxHsAgP7M3qOplZkFt4AaABAg",
    "video_id": "abc123xyz",
    "channel_id": "UCvZ_9N7JRRb-tM_qh9Bx1ew",
    "parent_comment_id": null,
    "author_channel_id": "UCuser123",
    "author_display_name": "Nguyen Van A",
    "text_original": "Pin trâu lắm, dùng cả ngày không hết",
    "text_display": "Pin trâu lắm, dùng cả ngày không hết",
    "like_count": 42,
    "reply_count": 3,
    "is_reply": false,
    "crawl_type": "full",
    "published_at": "2026-04-06T09:00:00Z",
    "updated_at": "2026-04-06T09:00:00Z",
    "crawled_at": "2026-04-09T07:35:00Z"
  }
]
```