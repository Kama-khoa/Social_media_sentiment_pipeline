# CLAUDE.md — dashboard/

## Mục tiêu

Giao diện trực quan tương tác hiển thị kết quả phân tích sentiment sản phẩm công nghệ Việt Nam. Gọi API từ `api/` để lấy dữ liệu, không query BigQuery trực tiếp.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `app.py` | Streamlit app — 3 tab tương tác: Bảng xếp hạng, Radar khía cạnh, Dòng thời gian |

---

## Luồng hoạt động

```
app.py (Streamlit)
    │
    ├── Tab 1: Bảng xếp hạng
    │   GET /api/ranking?limit=10&category=smartphone
    │   → Bảng sắp xếp theo Bayesian score
    │   → Badge controversy index (màu cam nếu > threshold)
    │
    ├── Tab 2: Radar khía cạnh
    │   Người dùng chọn sản phẩm từ dropdown
    │   GET /api/radar/{product_id}
    │   → Plotly radar chart: 6 trục = 6 aspect labels
    │   → So sánh 2 sản phẩm cùng lúc (overlay)
    │
    └── Tab 3: Dòng thời gian
        GET /api/timeline/{product_id}
        → Plotly line chart: daily sentiment score
        GET /api/events/{product_id}
        → Đánh dấu change points trên chart
        → Hiển thị giải thích nguyên nhân (tiếng Việt)
```

---

## Thông tin bảo mật

- `API_BASE_URL` — URL của FastAPI server (thêm vào `.env`, mặc định `http://localhost:8000`)
- Dashboard không cần GCP credentials — toàn bộ data đi qua API

---

## Công nghệ và thư viện

| Thư viện | Version | Mục đích |
|---|---|---|
| `streamlit` | 1.42.0 | Web app framework |
| `plotly` | 5.24.1 | Radar chart, line chart tương tác |
| `requests` | 2.32.3 | Gọi FastAPI endpoints |

---

## Chạy dashboard

```bash
streamlit run dashboard/app.py
```

---

## Yêu cầu hiệu năng

- Thời gian phản hồi mỗi click < 2 giây (đảm bảo bởi Redis cache bên API)
- Chuẩn bị video demo sẵn phòng mất mạng khi bảo vệ đồ án
