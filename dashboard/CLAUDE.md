# CLAUDE.md — dashboard/

## Trạng thái

`dashboard/` là Streamlit prototype cũ và không tiếp tục phát triển trong
Phase 5. Frontend chính thức nằm trong `frontend/` và dùng Next.js App Router
+ TypeScript.

Không thêm tính năng mới vào `dashboard/app.py`. Chỉ giữ thư mục này để tham
khảo hoặc xóa sau khi Next.js frontend đạt đủ Definition of Done.

---

## Luồng thay thế

```text
frontend/ (Next.js)
    |
    v
api/ (FastAPI)
    ├── BigQuery analytics và config
    ├── Redis cache
    ├── SQLAlchemy auth store
    └── Airflow REST API proxy cho Admin Pipeline Health
```
