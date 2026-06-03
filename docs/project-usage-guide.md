# Hướng Dẫn Sử Dụng Toàn Bộ Dự Án

Tài liệu này là runbook tổng hợp để chạy `Social Media Sentiment Pipeline` từ lúc khởi tạo schema, thu thập dữ liệu, xử lý NLP, tạo marts analytics, đến khi mở API và frontend.

## 1. Chuẩn Bị Môi Trường

Luôn chạy bằng Conda env của dự án:

```powershell
conda activate etl-py313
```

File `.env` ở thư mục root cần có tối thiểu:

```env
GCP_PROJECT_ID=...
GCS_BUCKET_NAME=...
BQ_DATASET=sentiment_platform
GOOGLE_APPLICATION_CREDENTIALS=...
YOUTUBE_API_KEY=...
GEMINI_API_KEY=...
POSTGRES_URL=...
JWT_SECRET_KEY=...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 2. Khởi Tạo BigQuery Schema

Chạy lần đầu hoặc khi cần tạo lại bảng:

```powershell
python -m schema.run_all
python schema\layer_1_raw\init_api_comment_tables.py
```

`schema.run_all` tạo các bảng chính và external tables đọc GCS. `init_api_comment_tables.py` tạo thêm:

- `raw_comments_api`: native table cho YouTube API comment backfill.
- `api_comment_backfill_state`: checkpoint từng video.

Nếu nâng cấp catalog sản phẩm:

```powershell
python -m schema.migrate_product_catalog
```

## 3. Seed Cấu Hình

Seed channel, keyword, product catalog và template specs thường được gọi trong `elt.main`. Nếu cần đồng bộ riêng, dùng `elt.seed_data.seed_loader` theo các helper hiện có trong code.

Catalog chuẩn nằm ở:

- `elt/seed_data/seed_products.csv`
- `product_config`
- `product_aliases`

Keyword chỉ dùng để discovery video, không dùng làm `product_id`.

## 4. Thu Thập Video Raw

Chạy toàn bộ ELT hiện có:

```powershell
python -m elt.main --mode full
```

Hoặc chạy riêng video:

```powershell
python -m elt.main --mode videos
```

Kết quả:

- Video raw lên GCS theo `raw/videos/...`
- `raw_videos` external table đọc từ GCS.
- `video_crawl_state` được cập nhật.

## 5. Tạo Candidate Video Cho API Comments

Sau khi video raw đã có, API comment backfill cần biết video nào liên quan đến sản phẩm trong catalog. Chạy:

```powershell
python scripts\dbt\dbt_runner.py run --select stg_youtube_videos int_video_product_mentions
```

Candidate được chọn từ:

```sql
stg_youtube_videos
JOIN int_video_product_mentions
```

## 6. Thu Thập Comments Bằng YouTube API

Kiểm tra candidate và quota trước:

```powershell
python scripts\run_api_comment_backfill.py --max-videos 10 --max-comments-per-video 100 --dry-run
```

Dry run không gọi API. Nếu thấy candidate hợp lý, chạy thật:

```powershell
python scripts\run_api_comment_backfill.py --max-videos 10 --max-comments-per-video 100
```

Ghi chú:

- Mỗi page `commentThreads.list` tốn 1 quota unit.
- Quota được quản lý bằng `QuotaBudget`.
- Quota đã dùng trong ngày được đọc từ `quota_operation_log` theo `DATE(created_at)`.
- Bucket quota là `youtube_api_comments`.
- Comments được `MERGE` vào `raw_comments_api` theo `comment_id`.
- Progress bar hiển thị số video, comments đã merge, quota đã dùng và status.

## 7. Rebuild Comments Và Sentence

Sau khi `raw_comments_api` có dữ liệu:

```powershell
python scripts\dbt\dbt_runner.py run --select stg_youtube_comments
python scripts\dbt\dbt_runner.py run --select int_comment_sentences --full-refresh
```

Lý do dùng `--full-refresh`: nếu trước đó sentence đã được tạo từ timestamp cũ của downloader, cần tạo lại để `published_at` mới đi xuống `fact_product_mentions.mention_date`.

## 8. Chạy NLP

Chạy NLP cho các sentence chưa xử lý:

```powershell
python -m nlp.runner
```

Chạy thử giới hạn:

```powershell
python -m nlp.runner --limit 500
```

Chạy lại bằng model/threshold mới:

```powershell
python -m nlp.runner --limit 500 --dag-run-id reprocess-t070 --reprocess
```

Kết quả NLP ghi vào:

- `raw_sentiment_results`
- Sau đó dbt promote lên `int_sentiment_results`

## 9. Rebuild Target, Fact Và Ranking

Chạy các model cần cho trang chủ/dashboard:

```powershell
python scripts\dbt\dbt_runner.py run --select int_sentiment_results int_sentence_product_targets fact_product_mentions agg_daily_product_ranking
```

Nếu cần resolve candidate mơ hồ trước khi rebuild fact:

```powershell
python -m nlp.product_target_resolver --limit 100
python scripts\dbt\dbt_runner.py run --select int_sentence_product_targets fact_product_mentions agg_daily_product_ranking
```

Trang chủ/dashboard đọc chủ yếu từ:

- `dim_products`
- `fact_product_mentions`
- `agg_daily_product_ranking`
- `causal_events` nếu dùng attribution

## 10. Chạy Analytics PELT

Chạy thử không ghi:

```powershell
python -m analytics.pelt_attribution --dry-run
```

Chạy thật:

```powershell
python -m analytics.pelt_attribution
```

PELT dùng `fact_product_mentions.mention_date`, nên timestamp comment API sẽ ảnh hưởng trực tiếp tới chuỗi thời gian.

## 11. Khởi Động API

Terminal 1:

```powershell
conda activate etl-py313
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Seed tài khoản demo nếu cần:

```powershell
python -m api.seed_admin
```

Swagger:

```text
http://localhost:8000/docs
```

## 12. Khởi Động Frontend

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Frontend chạy tại:

```text
http://localhost:3000
```

## 13. Checklist Sau Khi Dashboard Không Có Dữ Liệu Mới

Kiểm tra theo thứ tự:

1. `raw_comments_api` đã có rows chưa.
2. `stg_youtube_comments` đã chọn `crawl_type='api_backfill'` cho comment trùng chưa.
3. `int_comment_sentences` đã full-refresh sau API comments chưa.
4. `raw_sentiment_results` đã có NLP output cho sentence mới chưa.
5. `int_sentiment_results` đã promote kết quả NLP chưa.
6. `fact_product_mentions` đã có `mention_date` mới chưa.
7. `agg_daily_product_ranking` đã rebuild chưa.
8. API/Redis cache có cần restart hoặc đợi TTL 300 giây không.

## 14. Lệnh Chạy Nhanh End-to-End Sau Khi Có Video Raw

```powershell
conda activate etl-py313

python schema\layer_1_raw\init_api_comment_tables.py
python scripts\dbt\dbt_runner.py run --select stg_youtube_videos int_video_product_mentions
python scripts\run_api_comment_backfill.py --max-videos 100 --max-comments-per-video 100 --dry-run
python scripts\run_api_comment_backfill.py --max-videos 100 --max-comments-per-video 100

python scripts\dbt\dbt_runner.py run --select stg_youtube_comments
python scripts\dbt\dbt_runner.py run --select int_comment_sentences --full-refresh
python -m nlp.runner
python scripts\dbt\dbt_runner.py run --select int_sentiment_results int_sentence_product_targets fact_product_mentions agg_daily_product_ranking
```

Sau đó mở API và frontend như mục 11-12.
