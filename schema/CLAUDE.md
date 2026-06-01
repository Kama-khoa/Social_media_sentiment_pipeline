# CLAUDE.md — schema/

## Mục tiêu

Khởi tạo toàn bộ schema BigQuery cho dự án theo từng layer độc lập.
Folder này phải được chạy **đầu tiên**, trước khi bất kỳ phase nào bắt đầu.
Mỗi script chạy thủ công, độc lập, idempotent (chạy lại không bị lỗi).

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `run_all.py` | Chạy tuần tự layer_0 → layer_4. Dùng khi setup môi trường mới từ đầu |
| `layer_0_config/init_config_tables.py` | Tạo 5 bảng config và tracking trong BQ: `channel_config`, `keyword_config`, `video_crawl_state`, `quota_daily_summary`, `quota_operation_log` |
| `layer_1_raw/init_raw_tables.py` | Tạo External Tables trong BQ trỏ vào GCS bucket. Dữ liệu vẫn nằm trên GCS, BQ chỉ đọc qua đây |
| `layer_2_staging/init_staging_tables.py` | Tạo managed tables staging: `stg_youtube_videos`, `stg_youtube_comments`. Schema phẳng, đã qua bước JSON flatten |
| `layer_3_intermediate/init_staging_tables.py` | Tạo bảng trung gian: `int_comment_sentences`, `int_sentiment_results`. Kết quả NLP được ghi vào đây |
| `layer_4_marts/init_marts_tables.py` | Tạo bảng phân tích cuối trong `<BQ_DATASET>_marts`: `dim_products`, `fact_product_mentions`, `agg_daily_product_ranking`, `causal_events` |

---

## Luồng hoạt động

```
run_all.py
    │
    ├── layer_0_config/init_config_tables.py   ← Phase 0: BQ tables quản lý hệ thống
    │       channel_config, keyword_config
    │       video_crawl_state
    │       quota_daily_summary, quota_operation_log
    │
    ├── layer_1_raw/init_raw_tables.py         ← Phase 1: External Tables (GCS → BQ)
    │       raw_videos, raw_comments
    │       Partition theo YYYY/MM/DD từ GCS path
    │
    ├── layer_2_staging/init_staging_tables.py ← Phase 2: Sau khi dbt staging chạy
    │       stg_youtube_videos
    │       stg_youtube_comments
    │
    ├── layer_3_intermediate/init_intermediate_tables.py ← Phase 3: Sau NLP pipeline
    │       int_comment_sentences
    │       int_sentiment_results
    │
    └── layer_4_marts/init_marts_tables.py     ← Phase 4: Analytics marts
            dim_products
            fact_product_mentions
            agg_daily_product_ranking
            causal_events
```

---

## Thông tin bảo mật

- `GCP_PROJECT_ID` — đọc từ `.env`
- `BQ_DATASET` — đọc từ `.env` (giá trị: `sentiment_platform`)
- `GCS_BUCKET_NAME` — đọc từ `.env` (giá trị: `product-sentiment-raw-1806`)
- `GOOGLE_APPLICATION_CREDENTIALS` — đọc từ `.env`, trỏ đến file service account JSON

Không bao giờ hardcode project ID hay credentials trong script.

---

## Công nghệ và thư viện

- `google-cloud-bigquery==3.27.0` — tạo và quản lý BQ tables
- `google-auth==2.37.0` — xác thực GCP
- `python-dotenv==1.1.0` — load `.env`

---

## Lưu ý quan trọng

- **Idempotent:** Mỗi script dùng `CREATE TABLE IF NOT EXISTS` hoặc kiểm tra tồn tại trước khi tạo
- **Layer 1 External Tables** phụ thuộc vào GCS partition path `raw/youtube/YYYY/MM/DD/` — convention này phải được `elt/extract/` tuân thủ
- Chạy từng layer theo đúng thứ tự, không bỏ qua layer nào
- Dataset `sentiment_platform` phải tồn tại trước khi chạy bất kỳ layer nào
