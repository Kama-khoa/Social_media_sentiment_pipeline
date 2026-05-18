# CLAUDE.md — transform/

## Mục tiêu

Biến đổi dữ liệu JSON thô từ GCS (qua BigQuery External Tables) thành các bảng SQL có cấu trúc chuẩn trong BigQuery. Đây là bước **T** của pipeline ELT, thực hiện hoàn toàn bằng **dbt**.

Luồng: `GCS (raw JSON)` → `layer_1 External Tables` → `dbt` → `layer_2 Staging` → `layer_3 Intermediate` → `layer_4 Marts`

---

## Chức năng và nhiệm vụ từng file

| File/Folder | Nhiệm vụ |
|---|---|
| `dbt_project.yml` | Cấu hình dbt project: tên, version, profile, đường dẫn models |
| `profiles.yml` | Kết nối BigQuery: project, dataset, credentials. **Không commit file này nếu chứa credentials** |
| `models/staging/stg_youtube_videos.sql` | Flatten JSON raw → bảng phẳng video (1 row = 1 video) |
| `models/staging/stg_youtube_comments.sql` | UNNEST mảng comments → bảng phẳng (1 row = 1 comment) |
| `models/intermediate/int_comment_sentences.sql` | Tách comment dài thành từng câu, chuẩn hóa text, ánh xạ từ lóng |
| `models/intermediate/int_sentiment_results.sql` | Lưu kết quả NLP: aspect label + sentiment score từng câu |
| `models/marts/dim_products.sql` | Dimension table: thông tin sản phẩm, hãng, danh mục |
| `models/marts/fact_product_mentions.sql` | Fact table: mỗi lần sản phẩm được đề cập trong 1 comment |
| `models/marts/agg_daily_product_ranking.sql` | Bảng tổng hợp hằng ngày: Bayesian score, controversy index, ranking |
| `seeds/vn_slang_dictionary.csv` | Từ điển từ lóng tiếng Việt → chuẩn. Dùng `dbt seed` để nạp vào BQ |

---

## Luồng hoạt động

```
BigQuery External Tables (layer_1_raw)
raw_videos, raw_comments ← trỏ tới GCS
        │
        ▼ dbt run --select staging
models/staging/
├── stg_youtube_videos     ← JSON_EXTRACT fields từ raw_videos
└── stg_youtube_comments   ← UNNEST comments array từ raw_comments
                             + data_quality_score (lọc spam/link)
        │
        ▼ dbt run --select intermediate
models/intermediate/
├── int_comment_sentences  ← tách câu + ánh xạ vn_slang_dictionary
└── int_sentiment_results  ← nhận kết quả từ nlp/ pipeline
                             (aspect label, sentiment, confidence)
        │
        ▼ dbt run --select marts
models/marts/
├── dim_products            ← master data sản phẩm
├── fact_product_mentions   ← join sentences + sentiment + products
└── agg_daily_product_ranking ← Bayesian score, controversy index
```

---

## dbt Commands

```bash
# Setup lần đầu
dbt deps
dbt seed                         # load vn_slang_dictionary.csv vào BQ

# Chạy theo layer
dbt run --select staging
dbt run --select intermediate
dbt run --select marts

# Test
dbt test

# Xem data lineage
dbt docs generate
dbt docs serve
```

---

## Thông tin bảo mật

- `profiles.yml` chứa thông tin kết nối BQ — **không commit** nếu dùng service account key
- Nên dùng Application Default Credentials (ADC) hoặc biến môi trường `GOOGLE_APPLICATION_CREDENTIALS`
- `GCP_PROJECT_ID`, `BQ_DATASET` — tham chiếu qua biến dbt trong `dbt_project.yml`

---

## Công nghệ và thư viện

| Công nghệ | Version | Mục đích |
|---|---|---|
| `dbt-bigquery` | 1.8.x | Framework transformation |
| `dbt-core` | 1.8.x | Core dbt engine |
| BigQuery | — | Target data warehouse |

---

## Data Quality

`stg_youtube_comments` tính `data_quality_score`:
- Trừ điểm nếu comment chứa URL
- Trừ điểm nếu comment < 5 ký tự
- Trừ điểm nếu comment toàn emoji
- Comment có score < 0.5 bị đánh dấu `is_spam = TRUE`

---

## Debug

Sử dụng file `run_dbt.bat` (Cách nhanh nhất): Vào thẳng terminal ở thư mục gốc, gõ lệnh: `run_dbt.bat`

Manual debug qua Python script (`scripts/dbt/dbt_runner.py`)
- Kiểm tra kết nối đến BigQuery có ổn không:
`conda run -n etl-py313 python scripts/dbt/dbt_runner.py debug`

- Chạy toàn bộ bước transform (giống hệt run_dbt.bat):
`conda run -n etl-py313 python scripts/dbt/dbt_runner.py run`

- Chỉ chạy lại một model cụ thể (VD: khi anh sửa file dim_products.sql và chỉ muốn chạy mình nó để test):
`conda run -n etl-py313 python scripts/dbt/dbt_runner.py run --select dim_products`

---

## Lưu ý Kỹ thuật
- **Location BigQuery**: Pipeline ETL tạo các bảng ngoại ở `asia-southeast1`. Do đó file `transform/profiles.yml` cũng phải trỏ đến `location: asia-southeast1`, nếu không dbt sẽ báo lỗi Not Found.
- **NDJSON Format**: Bảng `raw_videos` và `raw_comments` là BigQuery External Tables trỏ tới GCS. Dữ liệu trên GCS bắt buộc phải được lưu ở chuẩn **NDJSON**.

---

## Lưu ý

- dbt chạy **độc lập** với ELT Python — không import code từ `elt/`
- `int_sentiment_results` phụ thuộc vào `nlp/` pipeline ghi kết quả vào BQ trước
- Models dbt nên có tests: `not_null` + `unique` trên primary keys
- Chạy `dbt run` sau khi GCS có dữ liệu mới và layer_1 External Tables đã detect partition mới
