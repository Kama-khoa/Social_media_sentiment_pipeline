# Progress Report & Updated Plan

## Cập Nhật 2026-05-30

### Trạng Thái Phase

| Phase | Module | Trạng thái | Ghi chú |
|---|---|---|---|
| Phase 0 | Schema BigQuery | Hoàn thành | Có thêm `raw_sentiment_results` cho NLP output |
| Phase 1 | ELT (`elt/`) | Hoàn thành | Thu thập dữ liệu và GCS/BQ raw ổn định |
| Phase 2 | Transform (`transform/dbt`) | Hoàn thành nền tảng | `int_sentiment_results` và `fact_product_mentions` đã nối với NLP output |
| Phase 3 | NLP Annotation | Hoàn thành | Gemini annotation + dataset preparation đã dùng cho training |
| Phase 3 | NLP Training | Hoàn thành | PhoBERT macro F1 khoảng `0.804`; vELECTRA NER F1 khoảng `0.90` |
| Phase 3 | NLP Inference | Hoàn thành vận hành | Local models load ổn, runner batch, debug mode, BigQuery MERGE/upsert, dbt promote |
| Phase 4 | Analytics Engine | Tiếp theo | Bayesian ranking, controversy index, PELT attribution |
| Phase 5 | Web App + RBAC | Sau Analytics | FastAPI, Redis, auth và một Next.js web app |

### NLP Acceptance Summary

- Model paths: `models/phobert_sentiment`, `models/velectra_aspect`.
- Confidence threshold: `0.70`.
- Debug file: `scratch/local_confidence_debug_500_t070.jsonl`.
- Debug 500 sentences: fallback tổng `6.0%`, fallback trên aspect thật `15.8%`.
- BigQuery flow: `raw_sentiment_results` -> `int_sentiment_results` -> `fact_product_mentions`.
- Reprocess support: `python -m nlp.runner --limit 500 --dag-run-id reprocess-t070 --reprocess`.

### Kế Hoạch Tiếp Theo

1. Chạy batch NLP đủ lớn để populate `fact_product_mentions`.
2. Hoàn thiện `agg_daily_product_ranking` bằng Bayesian score và controversy index.
3. Kiểm thử analytics trên dữ liệu thật, rà soát top products/aspects có hợp lý không.
4. Hoàn thiện PELT attribution trên chuỗi sentiment theo ngày.
5. Sau khi analytics ổn, chuyển sang web app FastAPI + Redis + Next.js với RBAC.

---
**Sentiment Intelligence Platform — Cập nhật 2026-05-19**

---

## 1. Trạng thái hiện tại theo Phase

| Phase | Module | Trạng thái | Ghi chú |
|---|---|---|---|
| Phase 0 | Schema BigQuery | Hoàn thành | Tất cả 12 bảng đã tạo |
| Phase 1 | ELT (`elt/`) | Hoàn thành | Phase A/B/C chạy ổn định |
| Phase 2 | Transform (`transform/dbt`) | Hoàn thành | Staging → Intermediate → Marts |
| Phase 3 | NLP Annotation | Hoàn thành | Bug rate limit đã sửa, đã thu thập đầy đủ câu |
| Phase 3 | NLP Training (Colab) | Hoàn thành | Dataset sạch và không leakage (prepare_dataset_v2.py). Đã vá Colab_Finetuning_Template.ipynb, sẵn sàng train lại với hyperparams tối ưu. |
| Phase 3 | NLP Inference | Đang thực hiện | Cấu trúc code có sẵn, sẵn sàng tích hợp khi có model weights mới |
| Phase 4 | Analytics Engine | Chưa bắt đầu | |
| Phase 5 | Web App + RBAC | Chưa bắt đầu | |
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
| **Guest/User** | Đăng ký, đăng nhập, đăng xuất. Tìm kiếm/lọc và xem các trang phân tích. |
| **Admin** | Toàn bộ quyền Guest + Quản lý kênh YouTube + Quản lý từ khóa tìm kiếm |

### 3.2 ELT Trigger khi Admin thêm Channel/Keyword mới — Sau MVP

Đây là phần mở rộng sau MVP. Khi triển khai tự động hóa, Admin thêm channel
hoặc keyword mới qua UI:
- Mặc định thực hiện backfill thu thập videos trong **30 ngày** kể từ ngày thêm.
- Admin có thể tùy chọn mốc thời gian (`lookback_days`).
- Trigger qua FastAPI endpoint → gọi vào `elt.main` module.

### 3.3 Airflow — 3 DAGs chính

| DAG | Tên | Schedule | Nhiệm vụ |
|---|---|---|---|
| 1 | `youtube_daily_extraction_dag` | 2:00 AM UTC+7 hằng ngày | Phase A (search.list) + Phase B (yt-dlp historical cho kênh mới) + Phase C (comment backlog) + dbt run |
| 2 | `sentiment_analysis_dag` | Sau `youtube_daily_extraction_dag` | Fetch câu chưa xử lý từ `int_comment_sentences` → inference vELECTRA + PhoBERT → confidence routing → ghi vào `int_sentiment_results` |
| 3 | `analytics_dag` | Sau `sentiment_analysis_dag` | Cần tạo sau Phase 4: Bayesian Ranking, Controversy Index, PELT Attribution → populate marts |

---

## 4. Plan thực hiện các phase còn lại

### Phase 3 — Hoàn thành NLP (Ưu tiên cao nhất)

```
Bước 3.1 — Auto-Annotation (chạy thủ công 1 lần)
  conda run -n etl-py313 python scratch/fetch_and_annotate_from_bq.py
  Output: data/export_for_colab/gemini_annotated_full.json và gemini_annotated_pos_neg.json

Bước 3.2 — Chuẩn bị và làm sạch data cho Colab (Chống Data Leakage)
  conda run -n etl-py313 python nlp/training/prepare_dataset_v2.py
  - Gộp các file JSON, xử lý trùng lặp, giải quyết conflict nhãn cảm xúc/NER.
  - Mix 20-30% nhãn NONE thật (bảo vệ vELECTRA khỏi False Positive).
  - Tách câu và split Train/Val đảm bảo no overlap (ngăn chặn rò rỉ dữ liệu).
  Output: data/sentiment/phobert/ và data/ner/velectra/ (train.jsonl, val.jsonl)

Bước 3.3 — Huấn luyện trên Google Colab (GPU T4)
  - Đồng bộ dataset_hf/ lên Google Drive
  - Chạy vá và thực thi nlp/training/Colab_Finetuning_Template.ipynb
  - PhoBERT: pyvi word tokenize, input format `aspect </s> sentence`, lr=1e-5.
  - vELECTRA: underthesea word tokenize, default Trainer (không dùng WeightedTokenTrainer), lr=1e-5, early stopping.
  Target: vELECTRA F1 >= 0.70, PhoBERT F1 >= 0.80

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

### Phase 5 — Một Web App với RBAC

```
5.1  FastAPI — Auth layer
     POST /auth/register → tạo tài khoản Guest/User
     POST /auth/login    → trả JWT access token (role: user | admin)
     POST /auth/logout   → kết thúc phiên phía client, revoke token nếu triển khai denylist
     GET  /auth/me       → trả thông tin user hiện tại
     Hash mật khẩu, không lưu plaintext; dependency kiểm tra role cho protected endpoints
     SQLite local + SQLAlchemy lưu app_users trong MVP; không dùng BigQuery làm user store

5.2  FastAPI — Guest/User endpoints
     GET /products/top/{category}      → top 10 Bayesian Score
     GET /products/{id}/aspects        → radar chart 6 aspects
     GET /products/{id}/attribution    → causal events timeline
     GET /search?q=...&category=...    → tìm kiếm + lọc sản phẩm
     GET /health                       → trạng thái hệ thống

5.3  FastAPI — Admin endpoints (role=admin required)
     GET    /admin/channels            → danh sách channel_config
     POST   /admin/channels            → thêm channel mới
     PUT    /admin/channels/{id}       → sửa channel
     DELETE /admin/channels/{id}       → xóa hoặc vô hiệu hóa channel
     GET    /admin/keywords            → danh sách keyword_config
     POST   /admin/keywords            → thêm keyword mới
     PUT    /admin/keywords/{id}       → sửa keyword
     DELETE /admin/keywords/{id}       → xóa hoặc vô hiệu hóa keyword
     CRUD config ghi trực tiếp BigQuery; ưu tiên soft delete is_active=FALSE

5.4  Next.js App Router — Guest/User view
     Auth: Đăng ký, đăng nhập, đăng xuất
     Page 1: Search & Filter — tìm kiếm và lọc dữ liệu sản phẩm
     Page 2: Top Products — bảng Bayesian Score, Controversy icon, bar chart
     Page 3: Product Detail — radar chart 6 aspects, top 5 bình luận
     Page 4: Attribution Timeline — biến động sentiment, causal events

5.5  Next.js App Router — Admin view
     Admin kế thừa toàn bộ quyền Guest/User
     Page 5: Channel Management — CRUD channel_config
     Page 6: Keyword Management — CRUD keyword_config
     Page 7: Pipeline Health — Airflow health, DAG runs, task status, BQ metrics

5.6  FastAPI — Airflow proxy (role=admin required)
     GET  /admin/pipeline/health                  → Airflow /health
     GET  /admin/pipeline/dags                    → Airflow /api/v1/dags
     GET  /admin/pipeline/dags/{dag_id}/runs      → lịch sử DAG runs
     GET  /admin/pipeline/dags/{dag_id}/runs/{run_id}/tasks → task instances
     POST /admin/pipeline/dags/{dag_id}/trigger   → trigger DAG có xác nhận
     GET  /admin/pipeline/metrics                 → quota, crawl state, NLP batch từ BQ

5.7  Sau MVP
     Trigger ELT backfill sau thay đổi channel/keyword nếu cần tự động hóa
     JWT denylist trong Redis nếu cần revoke access token ngay lập tức
```

### Airflow — 3 DAGs

```
airflow/dags/youtube_daily_extraction_dag.py
  schedule: "0 19 * * *"  (2:00 AM UTC+7 = 19:00 UTC ngày trước)
  tasks:
    sync_seed_data >> run_phase_a >> run_phase_b >> run_phase_c >> dbt_run

airflow/dags/sentiment_analysis_dag.py
  schedule: sau youtube_daily_extraction_dag (sensor hoặc fixed offset +2h)
  tasks:
    fetch_unprocessed_sentences >> run_nlp_inference >> write_sentiment_results

airflow/dags/analytics_dag.py  # cần tạo khi Phase 4 hoàn chỉnh
  schedule: sau sentiment_analysis_dag (fixed offset +1h)
  tasks:
    compute_bayesian_ranking >> compute_controversy >> run_pelt_attribution >> refresh_marts
```

---

## 5. Cấu trúc thư mục cần tạo mới

```
api/
├── main.py              ← FastAPI app entry point
├── auth.py              ← Register/login/logout, JWT, password hashing
├── database.py          ← SQLAlchemy session, SQLite local cho app_users
├── models.py            ← User model và role user|admin
├── routers/
│   ├── products.py      ← Guest endpoints
│   ├── search.py        ← Search/filter endpoint
│   ├── admin.py         ← Admin endpoints (channel/keyword CRUD)
│   └── pipeline.py      ← Airflow proxy và BQ operational metrics
└── dependencies.py      ← get_current_user, require_admin

frontend/
├── app/
│   ├── (auth)/          ← login, register
│   ├── analytics/       ← search, top-products, product detail, attribution
│   └── admin/           ← channels, keywords, pipeline-health
├── components/          ← shadcn/ui và chart components
├── lib/
│   └── api-client.ts    ← Gọi FastAPI, không gọi BQ/Airflow trực tiếp
└── package.json

airflow/dags/
├── youtube_daily_extraction_dag.py
├── sentiment_analysis_dag.py
├── seed_sync_dag.py
└── analytics_dag.py      ← cần tạo sau khi Phase 4 hoàn chỉnh

nlp/
└── runner.py            ← Script inference hằng ngày (gọi bởi sentiment_analysis_dag)

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
JWT_SECRET_KEY=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
APP_DATABASE_URL=sqlite:///./data/web_app.db
AIRFLOW_BASE_URL=http://localhost:8080
AIRFLOW_API_USERNAME=admin
AIRFLOW_API_PASSWORD=change_me

# Next.js frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 7. Kế hoạch triển khai Web App Phase 5

| Bước | Hạng mục | Kết quả cần đạt |
|---|---|---|
| 1 | Chốt contract API và schema | Pydantic schemas, lỗi `401/403/404`, query params tìm kiếm/lọc |
| 2 | Auth storage và RBAC | SQLite migration, hash mật khẩu, JWT, seed một admin local |
| 3 | Guest/User API | Search/filter và ba nhóm analytics endpoint đọc marts |
| 4 | Admin API | CRUD keyword/channel trực tiếp BigQuery, validate input, invalidate cache |
| 5 | Next.js auth shell | Register/login/logout, route guard, role-based navigation |
| 6 | Trang Guest/User | Search & Filter, Top Products, Product Detail, Attribution Timeline |
| 7 | Trang Admin | Channel Management, Keyword Management, Pipeline Health |
| 8 | Airflow proxy | Health, DAG runs, task status, trigger DAG và BQ operational metrics |
| 9 | Kiểm thử | Unit API, RBAC `403`, integration Redis, smoke test theo hai role |
| 10 | Đóng gói | Docker Compose local, `.env.example`, video demo |

**Definition of Done MVP**

- Guest/User hoàn thành đăng ký, đăng nhập, đăng xuất, tìm kiếm/lọc và xem
  các trang phân tích trong cùng một web app.
- Admin có toàn bộ quyền Guest/User và CRUD được từ khóa, kênh tìm kiếm.
- Admin theo dõi được Airflow health, DAG runs, task status và BQ metrics.
- FastAPI trả `403` khi user thường gọi trực tiếp endpoint `/admin/*`.
- Mật khẩu chỉ tồn tại dưới dạng hash; secret chỉ đọc từ `.env`.
- Endpoint analytics sau cache phản hồi dưới 2 giây.

---

## 8. Thứ tự ưu tiên thực hiện

1. **Annotation xong** → chạy `scratch/fetch_and_annotate_from_bq.py` với fix rate limit mới
2. **Training Colab** → vELECTRA + PhoBERT weights
3. **NLP inference runner** → `nlp/runner.py` cho DAG
4. **Analytics dbt models** → Bayesian + Controversy
5. **PELT Attribution** → `analytics/pelt_attribution.py`
6. **FastAPI auth + endpoints**
7. **Một Next.js web app** với RBAC
8. **3 Airflow DAGs**
