# CLAUDE.md — api/

## Mục tiêu

Cung cấp REST API backend cho dashboard Streamlit, query BigQuery và cache kết quả bằng Redis để giảm tải và đảm bảo thời gian phản hồi < 2 giây.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `main.py` | Khởi tạo FastAPI app, đăng ký routers, kết nối Redis, cấu hình CORS |
| `routers/sentiment_router.py` | 4 API endpoints chính: ranking, aspect radar, timeline, causal events |
| `schemas/response_schemas.py` | Pydantic models định nghĩa cấu trúc JSON response cho từng endpoint |

---

## Luồng hoạt động

```
Streamlit (dashboard/)
    │ HTTP request
    ▼
main.py (FastAPI app)
    │
    ▼
routers/sentiment_router.py
    │
    ├── Kiểm tra Redis cache (TTL=300s)
    │   ├── Cache hit  → trả về ngay
    │   └── Cache miss
    │           │
    │           ▼
    │       Query BigQuery
    │       (agg_daily_product_ranking, fact_product_mentions, causal_events)
    │           │
    │           ▼
    │       Ghi vào Redis cache
    │           │
    │           ▼
    └── Response (schemas/response_schemas.py)
```

---

## 4 API Endpoints

| Endpoint | Method | Mô tả | BQ Source |
|---|---|---|---|
| `/api/ranking` | GET | Top N sản phẩm theo Bayesian score + controversy | `agg_daily_product_ranking` |
| `/api/radar/{product_id}` | GET | Điểm 6 khía cạnh của 1 sản phẩm (radar chart data) | `fact_product_mentions` |
| `/api/timeline/{product_id}` | GET | Chuỗi thời gian sentiment theo ngày | `agg_daily_product_ranking` |
| `/api/events/{product_id}` | GET | Sự kiện nhân quả đã phân tích | `causal_events` |

---

## Thông tin bảo mật

| Biến | Mục đích |
|---|---|
| `GCP_PROJECT_ID`, `BQ_DATASET` | Query BigQuery |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP auth |
| `REDIS_HOST` | Redis connection (thêm vào .env) |
| `REDIS_PORT` | Redis connection (thêm vào .env) |

---

## Công nghệ và thư viện

| Thư viện | Version | Mục đích |
|---|---|---|
| `fastapi` | 0.115.6 | Web framework |
| `uvicorn` | 0.34.0 | ASGI server |
| `redis` | 5.2.1 | Cache layer (TTL=300s) |
| `google-cloud-bigquery` | 3.27.0 | Query BQ |
| `pydantic` | (bundled với fastapi) | Response schemas |

---

## Chạy server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
