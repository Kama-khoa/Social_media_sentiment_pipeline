# CLAUDE.md — api/

## Trạng thái hiện tại (2026-06-01)

Phase 5 MVP đã triển khai xong các thành phần cốt lõi:

| File | Trạng thái | Nhiệm vụ |
|---|---|---|
| `main.py` | Hoàn thành | FastAPI app, CORS, startup hook init DB |
| `config.py` | Hoàn thành | Đọc env vars qua `os.getenv`, `lru_cache` |
| `auth.py` | Hoàn thành | bcrypt hash, JWT tạo/verify (`python-jose`) |
| `database.py` | Hoàn thành | SQLAlchemy + PostgreSQL, auto-create DB nếu chưa có |
| `models.py` | Hoàn thành | `AppUser` (id, email, hashed_password, role, is_active) |
| `dependencies.py` | Hoàn thành | `get_current_user`, `require_admin` |
| `seed_admin.py` | Hoàn thành | Tạo 2 tài khoản demo khi setup lần đầu |
| `routers/auth.py` | Hoàn thành | `/auth/register`, `/login`, `/logout`, `/me` |
| `routers/dashboard.py` | Hoàn thành (mock data) | `/dashboard/user`, `/dashboard/admin` |
| `schemas/request_schemas.py` | Hoàn thành | `RegisterRequest`, `LoginRequest` |
| `schemas/response_schemas.py` | Hoàn thành | Tất cả response types |
| `routers/products.py` | Chưa tạo | Cần implement khi BQ marts có data |
| `routers/search.py` | Chưa tạo | Cần implement sau analytics |
| `routers/admin.py` | Chưa tạo | CRUD channel/keyword → BigQuery |
| `routers/pipeline.py` | Chưa tạo | Airflow REST API proxy |

---

## Chạy server

### Yêu cầu

- Conda environment `etl-py313` đã kích hoạt
- PostgreSQL đang chạy và biến `POSTGRES_URL` trong `.env` hợp lệ
- Đã cài thêm: `passlib[bcrypt]`, `python-jose[cryptography]`, `email-validator`, `psycopg2-binary`

```powershell
# Cài dependencies bổ sung (chỉ cần làm 1 lần)
conda activate etl-py313
pip install "passlib[bcrypt]==1.7.4" "python-jose[cryptography]==3.5.0" "email-validator==2.3.0" "psycopg2-binary" "bcrypt==4.2.1"
```

### Khởi động

```powershell
# Từ thư mục gốc project
conda activate etl-py313
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Server khởi động tại `http://localhost:8000`. Lần đầu chạy sẽ tự động:
1. Tạo database PostgreSQL nếu chưa tồn tại (đọc từ `POSTGRES_URL`).
2. Chạy `CREATE TABLE IF NOT EXISTS` cho bảng `app_users`.

### Seed tài khoản demo

```powershell
# Chỉ cần chạy 1 lần sau khi server đã start thành công
conda activate etl-py313
python -m api.seed_admin
```

Tạo ra 2 tài khoản:

| Email | Mật khẩu | Role |
|---|---|---|
| `admin@example.com` | `admin1234` | `admin` |
| `user@example.com` | `user1234` | `user` |

### Interactive API docs

Sau khi server chạy, truy cập:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Cấu trúc file thực tế

```
api/
├── __init__.py
├── CLAUDE.md
├── config.py             ← Settings từ env vars, lru_cache singleton
├── auth.py               ← bcrypt + JWT (python-jose)
├── database.py           ← SQLAlchemy engine PostgreSQL, auto-create DB
├── models.py             ← AppUser ORM model
├── dependencies.py       ← get_current_user, require_admin FastAPI deps
├── seed_admin.py         ← Script seed 2 demo accounts
├── main.py               ← FastAPI app entry point
├── routers/
│   ├── __init__.py
│   ├── auth.py           ← /auth/* endpoints
│   └── dashboard.py      ← /dashboard/user, /dashboard/admin (mock data)
└── schemas/
    ├── __init__.py
    ├── request_schemas.py
    └── response_schemas.py
```

---

## Environment Variables

Đọc từ `.env` ở thư mục gốc project. `api/config.py` dùng `os.getenv` với fallback mặc định.

| Biến | Giá trị mặc định | Bắt buộc | Mục đích |
|---|---|---|---|
| `POSTGRES_URL` | — | Có | PostgreSQL connection string cho `app_users` |
| `APP_DATABASE_URL` | _(đọc từ POSTGRES_URL)_ | Không | Override nếu muốn dùng URL khác với POSTGRES_URL |
| `JWT_SECRET_KEY` | `dev-secret-change-in-prod-123456` | Có (prod) | Ký JWT, đổi giá trị trong production |
| `JWT_ALGORITHM` | `HS256` | Không | Thuật toán JWT |
| `JWT_EXPIRE_MINUTES` | `480` | Không | Thời gian sống token (8 giờ) |
| `REDIS_HOST` | `localhost` | Không | Redis host (dùng khi implement cache) |
| `REDIS_PORT` | `6379` | Không | Redis port |
| `AIRFLOW_BASE_URL` | `http://localhost:8080` | Không | Airflow webserver URL |
| `AIRFLOW_API_USERNAME` | `admin` | Không | Airflow Basic Auth username |
| `AIRFLOW_API_PASSWORD` | `admin` | Không | Airflow Basic Auth password |
| `GCP_PROJECT_ID` | — | Có (analytics) | GCP project ID cho BigQuery |
| `BQ_DATASET` | — | Có (analytics) | BigQuery dataset (`sentiment_platform`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Có (analytics) | Path đến GCP service account JSON |

**Logic đọc `APP_DATABASE_URL`:**
```python
app_database_url = os.getenv("APP_DATABASE_URL") or os.getenv("POSTGRES_URL", fallback)
```
→ Ưu tiên `APP_DATABASE_URL` nếu set, fallback sang `POSTGRES_URL`.

---

## API Contract — Endpoints hiện có

### `GET /health`

Public. Không cần auth.

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "sentiment-api"}
```

---

### `POST /auth/register`

Tạo tài khoản mới với role `user`.

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "mypassword", "display_name": "Nguyễn Văn A"}'

# Response 201:
# {"id": "uuid", "email": "...", "display_name": "...", "role": "user", "created_at": "..."}
# Response 409 nếu email đã tồn tại
```

**Validation:**
- `email`: phải là email hợp lệ (dùng `email-validator`)
- `password`: tối thiểu 8 ký tự
- `display_name`: tối thiểu 2 ký tự

---

### `POST /auth/login`

Trả JWT access token.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin1234"}'

# Response 200:
# {"access_token": "eyJ...", "token_type": "bearer", "role": "admin"}
# Response 401 nếu sai credentials
```

Token chứa payload: `{"sub": "<user_id>", "role": "admin|user", "exp": <timestamp>}`

---

### `POST /auth/logout`

Cần Bearer token. MVP: stateless — client tự xóa token.

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <token>"
# Response 204 No Content
```

---

### `GET /auth/me`

Cần Bearer token.

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"

# Response 200:
# {"id": "...", "email": "...", "display_name": "...", "role": "admin", "created_at": "..."}
# Response 401 nếu token invalid/expired
```

---

### `GET /dashboard/user`

Cần Bearer token (bất kỳ role nào). Hiện trả mock data.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"user1234"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/dashboard/user \
  -H "Authorization: Bearer $TOKEN"
```

**Response schema:**
```json
{
  "category_stats": [{"category": "dien_thoai", "label": "Điện thoại", "mention_count": 1204, "week_change_pct": 12.3}],
  "top_products": [{"rank": 1, "product_id": "...", "product_name": "...", "bayesian_score": 0.72, "controversy_label": "low", ...}],
  "latest_causal_events": [{"product_name": "...", "change_point_date": "2026-05-28", "sentiment_direction": "POSITIVE", ...}],
  "as_of_date": "2026-06-01"
}
```

---

### `GET /dashboard/admin`

Cần Bearer token với `role=admin`. User thường → HTTP 403.

```bash
curl http://localhost:8000/dashboard/admin \
  -H "Authorization: Bearer <admin_token>"
```

**Response schema:**
```json
{
  "pipeline_status": {"airflow_webserver": "healthy", "quota_used_today": 1800, "quota_limit": 10000, ...},
  "quick_stats": {"videos_today": 34, "comments_today": 1204, "products_tracked": 47, ...},
  "recent_dag_runs": [{"dag_id": "youtube_daily_extraction_dag", "state": "success", "duration_seconds": 252, ...}],
  "attention_items": [{"level": "warning", "message": "..."}],
  "as_of_date": "2026-06-01"
}
```

---

## RBAC — Cơ chế bảo vệ

```python
# dependencies.py
def get_current_user(credentials, db) → AppUser:
    # Decode JWT → lấy sub (user_id)
    # Query db.app_users WHERE id = sub
    # 401 nếu token invalid, user không tồn tại, hoặc is_active=False

def require_admin(current_user) → AppUser:
    # Gọi get_current_user trước
    # 403 nếu role != "admin"
```

Mọi endpoint `/admin/*` phải dùng `Depends(require_admin)`. Frontend ẩn menu Admin chỉ là UX — FastAPI là nơi enforce thực sự.

---

## Mock Data — dashboard.py

`routers/dashboard.py` hiện trả hardcoded mock data. Khi chuyển sang data thật:

1. **User dashboard** → query `agg_daily_product_ranking` và `causal_events` từ BigQuery.
2. **Admin dashboard** → gọi Airflow `/health`, `/api/v1/dags/{dag_id}/dagRuns` và query `quota_daily_summary` từ BigQuery.

Thứ tự implement tiếp theo:
```
routers/products.py   ← GET /products/top/{category}, /products/{id}/aspects, /products/{id}/attribution
routers/search.py     ← GET /search?q=&category=
routers/admin.py      ← CRUD keyword_config và channel_config trong BigQuery
routers/pipeline.py   ← Proxy Airflow REST API
```

---

## Lưu ý kỹ thuật

- **bcrypt phiên bản**: phải dùng `bcrypt==4.2.1`. Phiên bản 5.x không tương thích với `passlib` và gây `AttributeError`.
- **Email domain**: `email-validator` từ chối domain nội bộ như `.local`. Dùng `@example.com` cho test accounts.
- **`_ensure_database_exists()`**: chạy ở module level khi import `database.py`. Nó connect đến database `postgres` và chạy `CREATE DATABASE` với `autocommit=True`. Nếu cần debug, set `POSTGRES_URL` đến một server có quyền tạo database.
- **CORS**: hiện chỉ cho phép `http://localhost:3000`. Khi deploy production, thêm production URL vào `allow_origins` trong `main.py`.
- **Deprecated `@app.on_event("startup")`**: FastAPI 0.115 vẫn hỗ trợ nhưng sẽ bị remove. Migration sang `lifespan` context manager nếu nâng cấp FastAPI sau này.
