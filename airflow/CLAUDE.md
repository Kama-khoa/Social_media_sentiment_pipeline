# CLAUDE.md — airflow/

## Mục tiêu

Tự động hóa toàn bộ pipeline hằng ngày bằng Apache Airflow. Folder này được tạo **SAU KHI** tất cả scripts trong `elt/` đã chạy thành công thủ công.

**Airflow chỉ import và gọi scripts từ `elt/` — không chứa business logic.**

---

## Quan trọng: Môi trường tách biệt

| | ELT Scripts | Airflow DAGs |
|---|---|---|
| Folder | `elt/` | `airflow/dags/` |
| Python | Conda: etl-py313 | Conda: etl-py313 (hoặc Docker tùy chọn) |
| Runtime | Trực tiếp | Local (đang chuyển đổi từ Docker) |
| Dependencies | `requirements.txt` | Airflow Local |

DAG **không được** import trực tiếp từ `elt/` Python packages — phải gọi qua `BashOperator` hoặc `PythonOperator` với subprocess.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ | Schedule |
|---|---|---|
| `dags/youtube_daily_extraction_dag.py` | Chạy video discovery (3 modes) + comment crawl | `@daily` 02:00 AM |
| `dags/sentiment_analysis_dag.py` | Chạy NLP inference pipeline (vELECTRA + PhoBERT + routing) | `@daily` 04:00 AM |
| `dags/seed_sync_dag.py` | Đồng bộ channel/keyword config mới khi có cập nhật CSV | Manual trigger |

---

## Luồng hoạt động

```
02:00 AM — youtube_daily_extraction_dag
    │
    ├── Task 1: init_quota_budget      ← query BQ, khởi tạo QuotaBudget
    ├── Task 2: run_historical_scan    ← Mode 0 yt-dlp (kênh chưa scan)
    ├── Task 3: run_rss_discovery      ← Mode 1 RSS (tất cả kênh)
    ├── Task 4: run_keyword_sweep      ← Mode 2 search.list
    ├── Task 5: crawl_comments         ← comment downloader + proxy
    └── Task 6: finalize_quota_summary ← ghi tổng kết quota vào BQ

04:00 AM — sentiment_analysis_dag (phụ thuộc extraction_dag xong)
    │
    ├── Task 1: run_velectra_extraction  ← aspect span detection
    ├── Task 2: run_phobert_classification ← sentiment scoring
    ├── Task 3: run_confidence_routing   ← fallback Gemini nếu < 0.70
    ├── Task 4: run_dbt_transform        ← dbt run staging+intermediate+marts
    ├── Task 5: run_bayesian_ranking     ← analytics/bayesian_ranking.py
    └── Task 6: run_pelt_attribution     ← analytics/pelt_attribution.py
```

---

## Retry Policy

```python
default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "retry_exponential_backoff": True,
}
```

---

## Thông tin bảo mật

- Credentials được truyền vào Docker container qua Airflow Connections hoặc Environment Variables
- Không hardcode bất kỳ key nào trong DAG files
- Airflow Variables store: `YOUTUBE_API_KEY`, `GEMINI_API_KEY`, `BRIGHTDATA_*`

---

## Công nghệ và thư viện

| Thư viện | Version | Mục đích |
|---|---|---|
| `apache-airflow` | 2.10.4 | Orchestration hiện tại theo `docker/Dockerfile.airflow` |
| `apache-airflow-providers-google` | compatible | GCP operators |

---

## Môi trường Chạy (Current State)

Dự án đang **chuyển đổi từ Docker-based deployment sang local development** để tránh hiện tượng overload session. 
Trong giai đoạn này:
- Khuyến nghị chạy pipeline manual qua các script trong `elt/` (ví dụ `conda run -n etl-py313 python -m elt.main`) hoặc qua các script bảo trì để linh hoạt hơn.
- Cấu hình Docker (`docker/docker-compose.yml`) vẫn được giữ lại để dùng cho production sau này.

Chạy Airflow bằng Docker Compose từ root project:

```powershell
docker compose --env-file .env -f docker\docker-compose.yml up airflow-webserver airflow-scheduler
```

---

## Lưu ý

- `catchup=False` trên tất cả DAGs — không chạy bù các ngày đã qua
- DAG `seed_sync_dag` chỉ chạy manual trigger khi thêm kênh/keyword mới
- Airflow UI tại `http://localhost:8080`

---

## Tích hợp Admin Pipeline Health

Next.js frontend không gọi Airflow trực tiếp. FastAPI proxy các endpoint Admin:

| FastAPI endpoint | Airflow 2.10.4 endpoint |
|---|---|
| `GET /admin/pipeline/health` | `GET /health` |
| `GET /admin/pipeline/dags` | `GET /api/v1/dags` |
| `GET /admin/pipeline/dags/{dag_id}/runs` | `GET /api/v1/dags/{dag_id}/dagRuns` |
| `POST /admin/pipeline/dags/{dag_id}/trigger` | `POST /api/v1/dags/{dag_id}/dagRuns` |

FastAPI phải giữ Airflow credentials phía server và enforce `require_admin`.
Health service cần kết hợp với DAG run status và BigQuery operational metrics;
`/health` đơn lẻ không chứng minh pipeline gần nhất chạy thành công.
