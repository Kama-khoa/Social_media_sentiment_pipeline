# CLAUDE.md — tests/

## Mục tiêu

Kiểm thử tự động từng layer của pipeline để đảm bảo tính đúng đắn trước khi tích hợp vào Airflow DAG. Mỗi sub-folder test tương ứng với 1 folder chính trong dự án.

---

## Chức năng và nhiệm vụ từng folder

| Folder | Nhiệm vụ |
|---|---|
| `test_elt/` | Test extract logic, GCS upload, repository queries, quota budget |
| `test_transform/` | Test dbt model output, data quality checks, schema validation |
| `test_nlp/` | Test annotation format, inference output, confidence routing logic |

---

## Luồng hoạt động

```
pytest tests/test_elt/        ← chạy sau khi code elt/ xong
pytest tests/test_transform/  ← chạy sau khi dbt models xong
pytest tests/test_nlp/        ← chạy sau khi inference pipeline xong

pytest tests/                 ← chạy toàn bộ
```

---

## Công nghệ và thư viện

| Thư viện | Version | Mục đích |
|---|---|---|
| `pytest` | 8.3.4 | Test framework |
| `unittest.mock` | stdlib | Mock BigQuery, GCS, API calls |

---

## Quy tắc

- Test file đặt tên `test_*.py`
- Mock toàn bộ external calls (BigQuery, GCS, YouTube API, Gemini) — không gọi API thật trong test
- Mỗi repository method có ít nhất 1 unit test
- Không để test làm thay đổi dữ liệu production trên BQ
