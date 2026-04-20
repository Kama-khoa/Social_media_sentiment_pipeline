# CLAUDE.md — elt/seed_data/

## Mục tiêu

Cung cấp dữ liệu đầu vào tối giản cho hệ thống. Người dùng chỉ cần cung cấp 2 file CSV đơn giản nhất có thể — mọi thông tin còn lại (channel_id, channel_name, subscriber_count, search_cluster, keyword_id...) đều được **tự động bổ sung** bởi `seed_loader.py` thông qua YouTube API.

Chạy thủ công 1 lần khi setup. Chạy lại khi muốn thêm kênh hoặc keyword mới.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `seed_channels.csv` | Input tối giản: chỉ có 1 cột `channel_handle` chứa URL đầy đủ của kênh |
| `seed_keywords.csv` | Input tối giản: có 3 cột `keyword_id` chứa id của từ khoá, `keyword_text` chứa từ khoá, `search_cluster` chứa từ khoá tìm kiếm |
| `seed_loader.py` | Script chạy thủ công — xử lý 2 CSV, gọi YouTube API để bổ sung thông tin, upsert vào BQ |

---

## Format CSV đầu vào thủ công

**seed_channels.csv** — chỉ 1 cột:
```
channel_handle
https://www.youtube.com/@realvatvostudio
https://www.youtube.com/@tgdd
https://www.youtube.com/@fptshop
https://www.youtube.com/@nguyenkim
```

**seed_keywords.csv** — 3 cột:
```
keyword_id, keyword_text, search_cluster
kw_080426001,Samsung Galaxy S25 review, Samsung Galaxy S25
kw_080426002,test pin Samsung Galaxy S25, Samsung Galaxy S25 
kw_080426003,Samsung Galaxy S25 Ultra, Samsung Galaxy S25 Ultra
kw_080426004,Samsung Galaxy S25+, Samsung Galaxy S25+
kw_080426005,iPhone 16 Pro Max, iPhone 16 Pro Max
kw_080426006,iPhone 16 Pro Max review, iPhone 16 Pro Max
kw_080426007,iPhone 16 Pro Max pin, iPhone 16 Pro Max
kw_080426008,review, _uncategorized
kw_080426009,so sánh, _uncategorized
kw_080426010,đánh giá, _uncategorized

```

---

## Luồng hoạt động của seed_loader.py

### Xử lý channel

```
seed_channels.csv
    │ đọc cột channel_handle
    │ parse "@handle" từ URL (VD: https://www.youtube.com/@tgdd → @tgdd)
    ▼
YouTube API: channels.list(forHandle="@tgdd")
    │ trả về: channel_id, channel_name, subscriber_count
    │ tự sinh: channel_url, created_at, last_updated_at
    │ mặc định: is_active=TRUE, is_historically_scanned=FALSE
    ▼
BigQuery MERGE → channel_config
```

### Xử lý keyword + Gemini cluster

```
seed_keywords.csv
    │ đọc toàn bộ keyword_text thành list
    ▼
Gemini API (1 lần gọi duy nhất):
    │ Input: toàn bộ list keywords
    │
    │ tự sinh: keyword_id = slugify(keyword_text)
    │ mặc định: is_active=TRUE, created_at=NOW
    ▼
BigQuery MERGE → keyword_config

```

**Nguyên tắc cluster — 2 loại:**

Loại 1 — Specific product: cluster name phải bằng chính xác tên model gốc,
và tên đó phải là 1 keyword_text có trong seed_keywords.csv.
Đây là điều kiện bắt buộc để Mode 2 trong video_extractor.py phát hiện
đúng loại cluster mà không cần thêm field mới vào schema.

    keyword_text                              search_cluster
    "Samsung Galaxy S25"                   →  "Samsung Galaxy S25"   ← cluster = keyword_text gốc
    "Samsung Galaxy S25 review tiếng việt" →  "Samsung Galaxy S25"
    "Samsung Galaxy S25 có tốt không"      →  "Samsung Galaxy S25"
    "Samsung Galaxy S25 Ultra"             →  "Samsung Galaxy S25 Ultra"  ← variant riêng
    "Samsung Galaxy S25+"                  →  "Samsung Galaxy S25+"        ← variant riêng

Loại 2 — Comparison / category: cluster name là nhãn tổng hợp mô tả
danh mục hoặc tiêu chí. Tên cluster không trùng với bất kỳ keyword_text
nào — đây là cách video_extractor nhận biết loại này.

    keyword_text                                   search_cluster
    "điện thoại tốt nhất tầm 5 triệu 2025"     →  "Điện thoại tầm 5 triệu"
    "điện thoại giá rẻ 5 triệu tốt nhất"       →  "Điện thoại tầm 5 triệu"
    "điện thoại chụp ảnh đẹp nhất 2025"        →  "Điện thoại camera tốt nhất"
    "bàn phím cơ tốt nhất 2025"               →  "Bàn phím cơ"
    "chuột không dây gaming tốt nhất"          →  "Chuột gaming không dây" 

---

## Thông tin bảo mật

| Biến | Mục đích |
|---|---|
| `YOUTUBE_API_KEY` | Gọi `channels.list` để lấy channel_id, tên, subscriber_count |
| `GEMINI_API_KEY` | Tự động sinh `search_cluster` cho từng keyword |
| `GCP_PROJECT_ID` | BigQuery project |
| `BQ_DATASET` | BigQuery dataset (`sentiment_platform`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng cho |
|---|---|---|
| `google-cloud-bigquery` | 3.27.0 | MERGE vào BQ channel_config, keyword_config |
| `google-generativeai` | 0.8.3 | Gemini API sinh search_cluster |
| `pandas` | 2.2.3 | Đọc CSV |
| `python-dotenv` | 1.1.0 | Load `.env` |
| `requests` | 2.32.3 | YouTube channels.list API call |

---

## Quota cost

| Bước | API | Cost |
|---|---|---|
| Resolve channel handles | YouTube `channels.list` | 1 unit / call, batch tối đa 50 handles/call |

Seed **không** tiêu thụ `bucket_search` — dùng `bucket_channel_seed` (500 units/ngày).

---

## Lưu ý

- `seed_loader.py` dùng BigQuery **MERGE** (upsert) — chạy lại không tạo duplicate
- Layer 0 schema phải tồn tại trước: `python schema/layer_0_config/init_config_tables.py`
- Sau khi seed xong, `elt/extract/video_extractor.py` đọc từ `channel_config` và `keyword_config`
- Không cần điền gì thêm vào CSV — chỉ cần URL kênh và keyword text là đủ