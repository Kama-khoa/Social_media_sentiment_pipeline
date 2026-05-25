# Progress Report & Updated Plan
**Sentiment Intelligence Platform — Cập nhật 2026-05-19**

---

## 1. Trạng thái hiện tại theo Phase

| Phase | Module | Trạng thái | Ghi chú |
|---|---|---|---|
| Phase 0 | Schema BigQuery | Hoàn thành | Tất cả 12 bảng đã tạo |
| Phase 1 | ELT (`elt/`) | Hoàn thành | Phase A/B/C chạy ổn định |
| Phase 2 | Transform (`transform/dbt`) | Hoàn thành | Staging → Intermediate → Marts |
| Phase 3 | NLP Annotation | Hoàn thành (fix) | Bug rate limit đã sửa |
| Phase 3 | NLP Training (Colab) | Chưa chạy | Chờ annotation xong |
| Phase 3 | NLP Inference | Chưa có weights | Cấu trúc code có sẵn |
| Phase 4 | Analytics Engine | Chưa bắt đầu | |
| Phase 5 | API + Dashboard | Chưa bắt đầu | |
| Airflow | DAGs | Chưa cấu hình | |

---

## 2. Các thay đổi đã thực hiện (2026-05-19)

### 2.1 Fix Rate Limit Gemini API

**File:** `nlp/annotation/gemini_annotator.py`

**Bug gốc:** Sau khi nhận 429 từ một model, code reset `limiter._last_call = 0.0`. Điều này khiến `_RateLimiter.wait()` tính ra `to_sleep` âm → batch tiếp theo gọi lại model bị 429 ngay lập tức không chờ → lại bị 429 → cascade không dừng.

**Các sửa đổi:**

| Thay đổi | Trước | Sau |
|---|---|---|
| Xử lý sau 429 | `limiter._last_call = 0.0` (bypass rate limiter) | `limiter.block_for_cooldown()` — block model 70s |
| Batch size default | 50 câu/request | 20 câu/request |
| RPD tracking | Không có | Class `_DailyBudget` per model |

**Class mới `_DailyBudget`:**
- Theo dõi số requests đã dùng trong ngày per model
- Tự reset khi sang ngày mới
- Skip model khi đã đạt RPD limit (gemini-2.5-flash chỉ có 500 RPD free tier)
- Log cảnh báo khi RPD còn ≤ 100

**Class cập nhật `_RateLimiter`:**
- Thêm field `_blocked_until: float`
- Thêm method `block_for_cooldown()` — set `_blocked_until = now + 70s`
- `wait()` kiểm tra cooldown trước khi tính khoảng cách RPM

**File:** `scratch/fetch_and_annotate_from_bq.py`

Refactor sang CLI đầy đủ:

```
--limit N         Số câu tối đa lấy từ BQ (mặc định 2000)
--batch-size N    Câu mỗi request Gemini (mặc định 20)
--min-words N     Số từ tối thiểu (mặc định 5)
--min-quality F   Điểm chất lượng tối thiểu (mặc định 0.8)
--output PATH     File output/checkpoint JSON
```

In ước tính trước khi chạy: số batch, thời gian dự kiến, cảnh báo RPD.

---

## 3. Yêu cầu mới (cập nhật kiến trúc)

### 3.1 Phân quyền (RBAC)

Hai role:

| Role | Quyền |
|---|---|
| **Guest (User)** | Xem 3 Dashboard tabs (Top sản phẩm, Aspect radar, Attribution timeline). Tìm kiếm và lọc sản phẩm. |
| **Admin** | Toàn bộ quyền Guest + Quản lý kênh YouTube + Quản lý từ khóa tìm kiếm |

### 3.2 ELT Trigger khi Admin thêm Channel/Keyword mới

Khi Admin thêm channel hoặc keyword mới qua UI:
- Mặc định thực hiện backfill thu thập videos trong **30 ngày** kể từ ngày thêm.
- Admin có thể tùy chọn mốc thời gian (`lookback_days`).
- Trigger qua FastAPI endpoint → gọi vào `elt.main` module.

### 3.3 Airflow — 3 DAGs chính

| DAG | Tên | Schedule | Nhiệm vụ |
|---|---|---|---|
| 1 | `dag_daily_elt` | 2:00 AM UTC+7 hằng ngày | Phase A (search.list) + Phase B (yt-dlp historical cho kênh mới) + Phase C (comment backlog) + dbt run |
| 2 | `dag_nlp` | Sau `dag_daily_elt` | Fetch câu chưa xử lý từ `int_comment_sentences` → inference vELECTRA + PhoBERT → confidence routing → ghi vào `int_sentiment_results` |
| 3 | `dag_analytics` | Sau `dag_nlp` | Tính Bayesian Ranking, Controversy Index, PELT Attribution → populate marts |

---

## 4. Plan thực hiện các phase còn lại

### Phase 3 — Hoàn thành NLP (Ưu tiên cao nhất)

```
Bước 3.1 — Auto-Annotation (chạy thủ công 1 lần)
  conda run -n etl-py313 python scratch/fetch_and_annotate_from_bq.py
  Output: data/export_for_colab/gemini_annotated_full.json

Bước 3.2 — Chuẩn bị data cho Colab
  conda run -n etl-py313 python nlp/training/prepare_colab_data.py
  Output: data/export_for_colab/dataset_hf/train.jsonl + val.jsonl

Bước 3.3 — Training trên Google Colab (GPU T4)
  Upload dataset_hf/ lên Google Drive
  Chạy nlp/training/finetune_velectra.py  → models/velectra_aspect/
  Chạy nlp/training/finetune_phobert.py   → models/phobert_sentiment/
  Target: vELECTRA F1 >= 0.70, PhoBERT accuracy >= 78%

Bước 3.4 — Tải weights về local và test inference
  python -c "from nlp.inference.confidence_router import ConfidenceRouter; ..."
```

### Phase 4 — Analytics Engine

```
4.1  dbt model: mart_product_ranking
     - Bayesian Score: (C × m + sum(w × s)) / (C + n), C=50, m=0.0
     - Controversy Index: Std(scores) / (|Mean(scores)| + 0.1)
     - Threshold: controversy > 0.6 = cao, 0.3-0.6 = trung bình, < 0.3 = thấp

4.2  Python: analytics/pelt_attribution.py
     - ruptures PELT, penalty=3, change point threshold biên độ > 0.25
     - Attribution score: temporal_proximity × 0.5 + direction_alignment × 0.5
     - Gemini Flash sinh câu giải thích tiếng Việt

4.3  BQ table: causal_events
     (product_id, change_point_date, event_video_id, attribution_score, explanation_text)
```

### Phase 5 — API + Dashboard (RBAC)

```
5.1  FastAPI — Auth layer
     POST /auth/login    → trả JWT token (role: admin | guest)
     Middleware kiểm tra role cho protected endpoints
     Env vars: AUTH_ENABLED, ADMIN_SECRET

5.2  FastAPI — Guest endpoints
     GET /products/top/{category}      → top 10 Bayesian Score
     GET /products/{id}/aspects        → radar chart 6 aspects
     GET /products/{id}/attribution    → causal events timeline
     GET /search?q=...&category=...    → tìm kiếm + lọc sản phẩm
     GET /health                       → trạng thái hệ thống

5.3  FastAPI — Admin endpoints (role=admin required)
     GET    /admin/channels            → danh sách channel_config
     POST   /admin/channels            → thêm channel mới + trigger ELT backfill
     DELETE /admin/channels/{id}       → xóa channel
     GET    /admin/keywords            → danh sách keyword_config
     POST   /admin/keywords            → thêm keyword mới + trigger ELT backfill
     DELETE /admin/keywords/{id}       → xóa keyword

5.4  Streamlit Dashboard — Guest view
     Tab 1: Top Products — bảng Bayesian Score, Controversy icon, bar chart
     Tab 2: Product Detail — radar chart 6 aspects, top 5 bình luận
     Tab 3: Attribution Timeline — biến động sentiment, causal events

5.5  Streamlit Dashboard — Admin view (thêm 2 tabs)
     Tab 4: Channel Management — CRUD channel_config, trigger backfill
     Tab 5: Keyword Management — CRUD keyword_config, trigger backfill
```

### Airflow — 3 DAGs

```
airflow/dags/dag_daily_elt.py
  schedule: "0 19 * * *"  (2:00 AM UTC+7 = 19:00 UTC ngày trước)
  tasks:
    sync_seed_data >> run_phase_a >> run_phase_b >> run_phase_c >> dbt_run

airflow/dags/dag_nlp.py
  schedule: sau dag_daily_elt (sensor hoặc fixed offset +2h)
  tasks:
    fetch_unprocessed_sentences >> run_nlp_inference >> write_sentiment_results

airflow/dags/dag_analytics.py
  schedule: sau dag_nlp (fixed offset +1h)
  tasks:
    compute_bayesian_ranking >> compute_controversy >> run_pelt_attribution >> refresh_marts
```

---

## 5. Cấu trúc thư mục cần tạo mới

```
api/
├── main.py              ← FastAPI app entry point
├── auth.py              ← JWT auth, role check middleware
├── routers/
│   ├── products.py      ← Guest endpoints
│   ├── search.py        ← Search/filter endpoint
│   └── admin.py         ← Admin endpoints (channel/keyword CRUD + ELT trigger)
└── dependencies.py      ← get_current_user, require_admin

dashboard/
├── app.py               ← Streamlit entry point, login page
├── pages/
│   ├── top_products.py
│   ├── product_detail.py
│   ├── attribution.py
│   ├── admin_channels.py
│   └── admin_keywords.py
└── utils/
    └── api_client.py    ← Gọi FastAPI từ Streamlit

airflow/dags/
├── dag_daily_elt.py
├── dag_nlp.py
└── dag_analytics.py

nlp/
└── runner.py            ← Script inference hằng ngày (gọi bởi dag_nlp)

analytics/
├── bayesian_ranking.py
├── controversy_index.py
└── pelt_attribution.py
```

---

## 6. Biến môi trường bổ sung

Thêm vào `.env` và `.env.example`:

```
# Auth
AUTH_ENABLED=true
ADMIN_SECRET=your_admin_password_here
JWT_SECRET_KEY=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

---

## 7. Thứ tự ưu tiên thực hiện

1. **Annotation xong** → chạy `scratch/fetch_and_annotate_from_bq.py` với fix rate limit mới
2. **Training Colab** → vELECTRA + PhoBERT weights
3. **NLP inference runner** → `nlp/runner.py` cho DAG
4. **Analytics dbt models** → Bayesian + Controversy
5. **PELT Attribution** → `analytics/pelt_attribution.py`
6. **FastAPI auth + endpoints**
7. **Streamlit Dashboard** với RBAC
8. **3 Airflow DAGs**
