# CLAUDE.md — airflow/

## Mục tiêu

Tự động hóa toàn bộ pipeline hằng ngày bằng Apache Airflow. Folder này được tạo **SAU KHI** tất cả scripts trong `elt/` đã chạy thành công thủ công.

**Airflow chỉ import và gọi scripts từ `elt/` — không chứa business logic.**

---

## Quan trọng: Môi trường tách biệt

| | ELT Scripts | Airflow DAGs |
|---|---|---|
| Folder | `elt/` | `airflow/dags/` |
| Python | 3.13.12 |
| Runtime | Trực tiếp | Docker container |
| Dependencies | `requirements.txt` | Airflow Docker image |

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
    ├── Task 3: run_confidence_routing   ← fallback Gemini nếu < 0.80
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
| `apache-airflow` | 3.1.8 | Orchestration (chạy trong Docker) |
| `apache-airflow-providers-google` | compatible | GCP operators |

---

## Docker Compose

Airflow chạy qua Docker Desktop trên Windows. Config nằm trong `docker-compose.yml` ở root (không commit nếu chứa credentials).

---

## Lưu ý

- `catchup=False` trên tất cả DAGs — không chạy bù các ngày đã qua
- DAG `seed_sync_dag` chỉ chạy manual trigger khi thêm kênh/keyword mới
- Airflow UI tại `http://localhost:8080`
