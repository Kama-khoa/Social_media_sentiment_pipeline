# Phase 5 — Web App: Hướng dẫn vận hành

> Cập nhật 2026-06-02: analytics pages, Admin CRUD và product catalog API đã được triển khai. Thiết kế nghiệp vụ đầy đủ nằm tại [`phase5-web-application.md`](phase5-web-application.md) và [`product-catalog-and-moderation.md`](product-catalog-and-moderation.md).

## Tổng quan

Phase 5 xây dựng một web app hoàn chỉnh gồm:

- **FastAPI** (`api/`) — REST API, auth, RBAC, data endpoints
- **Next.js** (`frontend/`) — UI cho Guest/User và Admin
- **PostgreSQL** — lưu `app_users` (auth store)

Frontend gọi FastAPI; FastAPI gọi BigQuery và Airflow. Không có kết nối trực tiếp từ frontend đến BigQuery hoặc Airflow.

---

## Yêu cầu

| Phần mềm | Phiên bản | Mục đích |
|---|---|---|
| Python | 3.13 (conda etl-py313) | Chạy FastAPI |
| Node.js | 20.9+ | Chạy Next.js |
| PostgreSQL | 14+ | Auth database |
| Conda environment | etl-py313 | Python runtime cho API |

### Python dependencies bổ sung (cài 1 lần)

```powershell
conda activate etl-py313
pip install "passlib[bcrypt]==1.7.4" "bcrypt==4.2.1" "python-jose[cryptography]==3.5.0" "email-validator==2.3.0" "psycopg2-binary" "fastapi==0.115.6" "uvicorn[standard]"
```

---

## Cấu hình .env

Thêm các biến sau vào `.env` ở thư mục gốc project (nếu chưa có):

```env
# PostgreSQL cho app_users
POSTGRES_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/<dbname>

# JWT
JWT_SECRET_KEY=<string-ngau-nhien-dai-32-ky-tu>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# Frontend URL (cho CORS)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`POSTGRES_URL` phải trỏ đến một PostgreSQL server đang chạy. Database sẽ tự động được tạo lần đầu khởi động API.

---

## Khởi động

### 1. Chạy FastAPI backend

```powershell
# Từ thư mục gốc project
conda activate etl-py313
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Lần đầu chạy, server tự động:
1. Tạo database (đọc tên từ `POSTGRES_URL`) nếu chưa tồn tại.
2. Tạo bảng `app_users`.

Kiểm tra: `http://localhost:8000/health` → `{"status": "ok"}`

### 2. Seed tài khoản demo

```powershell
conda activate etl-py313
python -m api.seed_admin
```

Tạo:

| Email | Mật khẩu | Role |
|---|---|---|
| `admin@example.com` | `admin1234` | admin |
| `user@example.com` | `user1234` | user |

Chỉ cần chạy 1 lần. Chạy lại sẽ bỏ qua nếu email đã tồn tại.

### 3. Chạy Next.js frontend

```powershell
cd frontend
npm install   # chỉ lần đầu
npm run dev
```

Frontend tại: `http://localhost:3000`

---

## Kiểm tra nhanh

```powershell
# 1. Health check
curl http://localhost:8000/health

# 2. Login lấy token
$response = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"admin@example.com","password":"admin1234"}'
$token = $response.access_token

# 3. Lấy dashboard admin
Invoke-RestMethod -Uri "http://localhost:8000/dashboard/admin" `
  -Headers @{Authorization = "Bearer $token"}

# 4. Thử với user thường → 403
$userResp = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"user@example.com","password":"user1234"}'
Invoke-RestMethod -Uri "http://localhost:8000/dashboard/admin" `
  -Headers @{Authorization = "Bearer $($userResp.access_token)"}
# → 403 Forbidden
```

---

## Kiến trúc API

```
POST   /auth/register        → Tạo tài khoản (role=user)
POST   /auth/login           → Lấy JWT access token
POST   /auth/logout          → Stateless logout (client xóa token)
GET    /auth/me              → Thông tin user hiện tại

GET    /dashboard/user       → Dashboard data cho user (any role)
GET    /dashboard/admin      → Dashboard data cho admin (role=admin only)

GET    /products/top/{category}               → Ranking theo product_id chuẩn
GET    /products/{product_id}/aspects         → Chi tiết, specs và aspect breakdown
GET    /products/{product_id}/attribution     → Timeline attribution
POST   /products/{product_id}/details/requests → User gửi phiếu chỉnh sửa
GET    /search?q=&category=                   → Tìm kiếm catalog

GET|POST|PUT|DELETE /admin/products
GET|POST|DELETE     /admin/products/aliases
GET|POST|DELETE     /admin/products/templates
GET                 /admin/products/detail-requests
POST                /admin/products/detail-requests/{request_id}/review
GET|PUT              /admin/products/video-mappings
GET|POST             /admin/products/resolution-candidates

GET    /health               → Health check public
```

### Phân quyền

| Endpoint | Auth yêu cầu |
|---|---|
| `POST /auth/register` | Không cần |
| `POST /auth/login` | Không cần |
| `GET /health` | Không cần |
| `GET /auth/me` | Bearer token hợp lệ |
| `GET /dashboard/user` | Bearer token hợp lệ (any role) |
| `GET /dashboard/admin` | Bearer token + `role=admin` |

---

## Luồng xác thực

```
Frontend                          FastAPI
   │                                │
   │  POST /auth/login              │
   │ ────────────────────────────► │
   │                                │ verify password (bcrypt)
   │                                │ tạo JWT {sub: user_id, role, exp}
   │  { access_token, role }        │
   │ ◄──────────────────────────── │
   │                                │
   │  sessionStorage.setItem(token) │
   │                                │
   │  GET /dashboard/user           │
   │  Authorization: Bearer <token> │
   │ ────────────────────────────► │
   │                                │ decode JWT → user_id
   │                                │ query app_users WHERE id=user_id
   │  { category_stats, ... }       │
   │ ◄──────────────────────────── │
```

Token hết hạn (mặc định 8 giờ) → `/auth/me` trả 401 → frontend redirect `/login`.

---

## Cấu trúc file đầy đủ

```text
Social_media_sentiment_pipeline/
├── .env                        ← Credentials (không commit)
├── api/
│   ├── CLAUDE.md               ← Hướng dẫn backend chi tiết
│   ├── __init__.py
│   ├── config.py               ← Settings từ env vars
│   ├── auth.py                 ← bcrypt + JWT
│   ├── database.py             ← SQLAlchemy + PostgreSQL
│   ├── models.py               ← AppUser ORM model
│   ├── dependencies.py         ← get_current_user, require_admin
│   ├── seed_admin.py           ← Seed demo accounts
│   ├── main.py                 ← FastAPI app entry point
│   ├── routers/
│   │   ├── auth.py             ← /auth/*
│   │   ├── dashboard.py        ← /dashboard/*
│   │   ├── products.py         ← ranking, details, specs, attribution
│   │   ├── search.py           ← tìm kiếm catalog
│   │   ├── admin.py            ← CRUD keyword/channel
│   │   ├── product_catalog.py  ← catalog, alias/template, candidate, mapping, moderation
│   │   └── pipeline.py         ← proxy Airflow
│   └── schemas/
│       ├── request_schemas.py
│       └── response_schemas.py
└── frontend/
    ├── CLAUDE.md               ← Hướng dẫn frontend chi tiết
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── page.tsx            ← redirect /dashboard
    │   ├── (auth)/             ← login, register
    │   ├── (app)/              ← dashboard và admin (route-guarded)
    │   └── (public)/           ← analytics pages
    ├── components/
    │   ├── Providers.tsx
    │   ├── layout/             ← Sidebar, Header
    │   ├── dashboard/          ← UserDashboard, AdminDashboard
    │   └── shared/             ← ControversyBadge
    └── lib/
        ├── api-client.ts
        ├── auth-context.tsx
        └── types.ts
```

---

## Tài khoản và phân quyền

| Role | Xem dashboard | Xem analytics | Admin CRUD | Pipeline health |
|---|---|---|---|---|
| `user` | UserDashboard | Có | Không | Không |
| `admin` | AdminDashboard | Có | Có | Có |

Dashboard phân biệt theo role. Analytics pages, CRUD keyword/channel, Pipeline Health và trang quản lý sản phẩm đã được triển khai.

---

## Xử lý lỗi thường gặp

### Port 8000 đang bận

```powershell
# Tìm và kill process đang dùng port 8000
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object {
  Stop-Process -Id $_.OwningProcess -Force
}
```

### Database không tồn tại

Lỗi `FATAL: database "xxx" does not exist` xảy ra khi:
- PostgreSQL chưa chạy, hoặc
- User trong `POSTGRES_URL` không có quyền tạo database

Kiểm tra:
```powershell
# Test kết nối PostgreSQL
conda activate etl-py313
python -c "import psycopg2; conn = psycopg2.connect('<POSTGRES_URL_không_có_+psycopg2>'); print('OK'); conn.close()"
```

### bcrypt 5.x không tương thích

```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

Giải pháp: `pip install "bcrypt==4.2.1"` (phiên bản 5.x phá vỡ passlib).

### Email domain bị từ chối

```
value is not a valid email address: The part after the @-sign is a special-use or reserved name
```

`email-validator` từ chối `.local`, `.internal`. Dùng `@example.com` cho test accounts.

### CORS blocked

Next.js gọi FastAPI bị blocked nếu:
- Frontend không chạy trên `http://localhost:3000`, hoặc
- `allow_origins` trong `api/main.py` chưa include origin của frontend

Sửa trong `api/main.py`:
```python
allow_origins=["http://localhost:3000", "http://localhost:3001"]
```

---

## Phát triển tiếp theo

### Endpoint đã triển khai

```
GET  /products/top/{category}          ← query agg_daily_product_ranking BQ
GET  /products/{id}                    ← query dim_products, fact_product_mentions
GET  /products/{id}/aspects            ← breakdown theo aspect từ int_sentiment_results
GET  /products/{id}/attribution        ← PELT change points
GET  /search?q=&category=              ← full-text search qua BQ
GET  /admin/channels                   ← đọc channel_config BQ
POST /admin/channels                   ← ghi channel_config BQ
DELETE /admin/channels/{id}            ← xóa channel_config BQ
GET  /admin/keywords                   ← đọc keyword_config BQ
POST /admin/keywords
DELETE /admin/keywords/{id}
GET  /admin/pipeline/health            ← Airflow REST API proxy
GET  /admin/pipeline/dag-runs          ← Airflow /api/v1/dags/.../dagRuns
POST /admin/pipeline/trigger/{dag_id}  ← Airflow trigger DAG
GET|POST|PUT|DELETE /admin/products    ← catalog chuẩn
GET|POST|DELETE /admin/products/aliases
GET|POST|DELETE /admin/products/templates
GET  /admin/products/detail-requests
POST /admin/products/detail-requests/{request_id}/review
```

### Hạng mục còn cần hoàn thiện

- Bổ sung UI đầy đủ cho alias/template specs, candidate resolution và phiếu moderation nếu cần tách khỏi trang Admin Products hiện tại.
- Bổ sung integration test với BigQuery test dataset cho quy trình duyệt phiếu.
- Chạy rebuild lịch sử sau migration catalog trước khi dùng ranking production.

---

## API docs tương tác

Khi FastAPI đang chạy:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Dùng Swagger UI để test endpoint trực tiếp không cần curl — click "Authorize", nhập Bearer token lấy từ `/auth/login`.
