# CLAUDE.md — analytics/

## Mục tiêu

Tính toán các chỉ số phân tích chuyên sâu từ dữ liệu sentiment đã xử lý: xếp hạng sản phẩm công bằng, đo lường mức độ tranh cãi, và truy vết nguyên nhân gốc rễ của các biến động cảm xúc bất thường.

---

## Chức năng và nhiệm vụ từng file

| File | Nhiệm vụ |
|---|---|
| `bayesian_ranking.py` | `BayesianRanking` class — tính Bayesian Score để xếp hạng sản phẩm công bằng, kéo điểm sản phẩm ít review về trung bình thống kê |
| `controversy_index.py` | `ControversyIndex` class — tính độ lệch chuẩn sentiment để phát hiện sản phẩm bị khen chê cực đoan (polarizing products) |
| `pelt_attribution.py` | `PELTAttribution` class — dùng thuật toán PELT (ruptures) để tìm điểm gãy sentiment, sau đó dùng Gemini giải thích nguyên nhân |

---

## Luồng hoạt động

```
BigQuery: agg_daily_product_ranking (từ dbt marts)
    │
    ├── bayesian_ranking.py
    │   │ đọc: fact_product_mentions (review_count, avg_sentiment)
    │   │ tính: bayesian_score = (n × mean + m × global_mean) / (n + m)
    │   └── ghi: agg_daily_product_ranking.bayesian_score
    │
    ├── controversy_index.py
    │   │ đọc: fact_product_mentions (sentiment_scores list)
    │   │ tính: controversy = std_deviation(sentiment_scores)
    │   └── ghi: agg_daily_product_ranking.controversy_index
    │
    └── pelt_attribution.py
        │ đọc: fact_product_mentions (chuỗi sentiment theo ngày, loại NONE)
        │
        ├── ruptures.Pelt(model="rbf").fit_predict()
        │   └── → change_points: [ngày_1, ngày_2, ...]
        │
        ├── Với mỗi change_point:
        │   query BQ: video có view_count cao trong ±7 ngày quanh điểm gãy
        │
        └── Gemini Flash: giải thích tương quan bằng tiếng Việt tự nhiên
            └── ghi vào: <BQ_DATASET>_marts.causal_events
```

---

## Công thức Bayesian Score

```
bayesian_score = (n × mean_i + m × global_mean) / (n + m)

Trong đó:
  n            = số reviews của sản phẩm i
  mean_i       = điểm sentiment trung bình của sản phẩm i
  m            = minimum reviews threshold (configurable, mặc định = 50)
  global_mean  = điểm sentiment trung bình toàn bộ sản phẩm
```

Sản phẩm có ít review sẽ bị kéo về `global_mean` — tránh sản phẩm 5 sao với 2 reviews vượt sản phẩm tốt thật sự.

---

## Controversy Index

```
controversy_index = std_deviation(sentiment_scores_of_product)

Cao  → sản phẩm bị khen chê cực đoan (polarizing)
Thấp → cộng đồng đồng thuận về sản phẩm
```

---

## PELT Algorithm (ruptures)

- **Model:** RBF (Radial Basis Function) — phát hiện thay đổi phân phối
- **Penalty:** tự động (BIC criterion)
- **Input:** chuỗi thời gian `daily_avg_sentiment` của 1 sản phẩm, nội suy gap tối đa 2 ngày
- **Output:** danh sách index ngày xảy ra thay đổi đột ngột
- **Readiness gate:** tối thiểu 10 ngày quan sát và coverage tối thiểu 70%

---

## Thông tin bảo mật

| Biến | Mục đích |
|---|---|
| `GEMINI_API_KEY` | Gọi Gemini Flash để giải thích nguyên nhân (pelt_attribution.py) |
| `GCP_PROJECT_ID`, `BQ_DATASET` | Đọc/ghi BigQuery |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP auth |

---

## Công nghệ và thư viện

| Thư viện | Version | Dùng trong | Mục đích |
|---|---|---|---|
| `ruptures` | 1.1.9 | `pelt_attribution.py` | PELT change point detection |
| `numpy` | 2.2.1 | tất cả | Tính toán thống kê |
| `scipy` | 1.15.1 | `controversy_index.py` | std_deviation, phân phối |
| `pandas` | 2.2.3 | tất cả | Xử lý time series |
| `google-generativeai` | 0.8.3 | `pelt_attribution.py` | Gemini giải thích nguyên nhân |
| `google-cloud-bigquery` | 3.27.0 | tất cả | Đọc/ghi BQ |

---

## Output

Kết quả ghi vào BigQuery:
- `agg_daily_product_ranking` — snapshot rolling 30 ngày với `bayesian_score`, `controversy_index`, `top_aspect`, `sentiment_trend`
- `<BQ_DATASET>_marts.causal_events` — bảng mới: `product_id`, `change_point_date`, `event_video_id`, `attribution_score`, `explanation_text`
