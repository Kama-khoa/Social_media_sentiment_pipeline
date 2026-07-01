# 🌟 Sentiment Intelligence Platform

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![dbt-bigquery](https://img.shields.io/badge/dbt-1.8-orange.svg)](https://www.getdbt.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-App_Router-000000.svg)](https://nextjs.org/docs/app)
[![Google Cloud Platform](https://img.shields.io/badge/GCP-BigQuery%20%7C%20GCS-4285F4.svg)](https://cloud.google.com/)

Hệ thống end-to-end thu thập, xử lý NLP lai (Hybrid) và phân tích cảm xúc (Sentiment Analysis) đa khía cạnh dành cho bình luận YouTube về các sản phẩm công nghệ Việt Nam (smartphone, laptop, smarthome). Đây là đồ án tốt nghiệp thiết kế theo tiêu chuẩn kỹ thuật và học thuật hiện đại.

---

## 📖 Giới thiệu Dự án

**Sentiment Intelligence Platform** là một giải pháp **Modern Data Stack** hoàn chỉnh, giải quyết các bài toán thực tế của xử lý dữ liệu lớn mạng xã hội:

- 🚀 **Bypass Quota Ingestion**: Thiết lập luồng thu thập dữ liệu lai thông minh. Sử dụng YouTube Data API v3 có kiểm soát định mức cho Phase A (Daily Scan). Sử dụng `yt-dlp` (0 quota) cho Phase B (Historical Scan) và `youtube-comment-downloader` (0 quota) thông qua **BrightData Residential Proxy** xoay vòng IP để cào bình luận số lượng lớn mà không bị chặn IP hay tốn chi phí quota.
- 🧠 **NLP Hybrid Pipeline**: Nhận diện khía cạnh bằng mô hình học sâu cục bộ `vELECTRA` (Aspect Extraction) và phân loại cảm xúc bằng `PhoBERT v2` (Sentiment Classification). Tích hợp cơ chế **Confidence-Routing** tự động định tuyến các câu có độ tin cậy thấp (< 0.70) sang Gemini Flash API làm chốt chặn bảo hiểm ngữ cảnh.
- 📊 **Advanced Analytics Engine**:
  - **Bayesian Sentiment Ranking**: Khắc phục thiên kiến sản phẩm ít review bằng cách kéo điểm về mức trung bình toàn cầu.
  - **Controversy Index**: Xác định mức độ bất đồng ý kiến của cộng đồng đối với sản phẩm.
  - **Correlation Attribution Engine**: Áp dụng thuật toán **PELT** phát hiện điểm gãy chuỗi thời gian, tính toán độ khớp tương quan với các video viral và tự động giải thích nguyên nhân bằng mô hình ngôn ngữ lớn (LLM).
- 🔐 **Web App & RBAC**: Phát triển FastAPI backend (Redis cache TTL 300s, PostgreSQL user store) cùng Next.js frontend (shadcn/ui, Recharts) phân quyền Guest/User và Admin chặt chẽ (enforced at API level).

---

## 🏗️ Kiến trúc Hệ thống & Luồng Dữ liệu

### 1. Kiến trúc Tổng thể (System Architecture)
```mermaid
graph TD
    %% Phase 1: Ingestion
    subgraph Phase1 [Giai đoạn 1: Data Ingestion]
        YT[YouTube Platform] -->|search.list per channel| API[YouTube Data API]
        YT -->|Comment Scraper| ID[youtube-comment-downloader]
        YT -->|Flat Extract Metadata| YTDL[yt-dlp]
        Bright[BrightData Residential Proxies] -->|Rotated IP Bypass rate limits| ID
        ID -->|Raw JSON| GCS[Google Cloud Storage Bucket]
        YTDL -->|Raw JSON| GCS
    end

    %% Phase 2: dbt Transformation
    subgraph Phase2 [Giai đoạn 2: Data Transformation dbt]
        GCS -->|NDJSON External Tables| BQ_STG[BigQuery Staging Layer]
        BQ_STG -->|JSON_EXTRACT & Quality Clean| BQ_INT[BigQuery Intermediate Layer]
        BQ_INT -->|JS UDF replace_slang| BQ_INT
    end

    %% Phase 3: NLP Hybrid Pipeline
    subgraph Phase3 [Giai đoạn 3: NLP Hybrid Pipeline]
        BQ_INT -->|int_comment_sentences| NLP_Runner[NLP Batch Runner]
        NLP_Runner -->|Sentence Text| Local_Models[Local Models Device]
        Local_Models -->|vELECTRA Base| NER[Token Aspect Classification]
        Local_Models -->|PhoBERT v2| Sent[Sequence Sentiment Classification]
        NER & Sent -->|Confidence Threshold < 0.70| Router[Confidence Router]
        Router -->|Fallback Low Confidence| Gemini[Gemini Flash API]
        NER & Sent -->|Accept High Confidence| BQ_RAW_RES[raw_sentiment_results BQ]
        Gemini -->|Structured Response| BQ_RAW_RES
    end

    %% Phase 4: Analytics Engine
    subgraph Phase4 [Giai đoạn 4: Analytics Engine]
        BQ_RAW_RES -->|dbt transformation| BQ_MARTS[BigQuery Marts Layer]
        BQ_MARTS -->|Bayesian Score & Controversy| BQ_RANK[agg_daily_product_ranking BQ]
        BQ_MARTS -->|Timeseries Sentiment| PELT[PELT Attribution Engine]
        PELT -->|ruptures RBF Change-point| Causal[Causal Video Attribution]
        Causal -->|Context Comments + Video| Gemini_Explain[Gemini Explanations]
        Gemini_Explain -->|Save Causal Event| BQ_CAUSAL[causal_events BQ]
    end

    %% Phase 5: Web Application
    subgraph Phase5 [Giai đoạn 5: Web Application]
        BQ_RANK & BQ_CAUSAL -->|Query data| FastAPI[FastAPI Backend Server]
        FastAPI -->|Redis cache TTL 300s| Redis[Redis Cache Server]
        FastAPI -->|Proxy Airflow REST API| Airflow[Apache Airflow DAGs]
        FastAPI -->|RBAC user/admin| Postgres[SQLAlchemy PostgreSQL App DB]
        FastAPI -->|JSON REST API| NextJS[Next.js App Router Frontend]
    end
```

### 2. Biểu đồ Tuần tự Dữ liệu (Data Flow Sequence Diagram)
```mermaid
sequenceDiagram
    participant ELT as ELT Scripts (Python)
    participant GCS as Google Cloud Storage
    participant BQ as BigQuery
    participant DBT as dbt (Transform)
    participant NLP as NLP Engine
    participant API as FastAPI Backend

    ELT->>ELT: Fetch Metadata & Comments
    ELT->>GCS: Upload raw data (NDJSON)
    ELT->>BQ: Update crawl_state (Log)
    BQ-->>DBT: Read from External Tables
    DBT->>DBT: Run Staging & Intermediate
    DBT->>BQ: Save flat structured tables
    BQ-->>NLP: Fetch un-processed text
    NLP->>NLP: Aspect & Sentiment Inference
    NLP->>BQ: Upsert raw_sentiment_results
    DBT->>BQ: Promote int_sentiment_results
    DBT->>BQ: Run Marts (Ranking & Analytics)
    API->>BQ: Query Analytics Data
    API->>API: Cache in Redis
    API-->>User: Return JSON Response
```

### 3. Biểu đồ Workflow Quá trình ELT (ELT 3-Phase Workflow)
```mermaid
flowchart LR
    subgraph "Phase A: Daily Scan"
        A1[YouTube API<br>search.list] --> A2[Filter Keywords]
        A2 --> A3[yt-dlp Enrich]
    end

    subgraph "Phase B: Historical Scan"
        B1[yt-dlp flat extract] --> B2[Batch 50 videos]
        B2 --> B3[yt-dlp Enrich]
    end

    subgraph "Phase C: Comment Backlog"
        C1[Query Maturity Model] --> C2[Comment Downloader]
        C2 --> C3[Extract Data]
    end

    A3 --> GCS[("GCS Bucket<br>(Raw JSON)")]
    B3 --> GCS
    C3 --> GCS
```

---

## 📊 Cơ sở Dữ liệu & BigQuery Schema (28 Bảng)

Hệ thống tổ chức BigQuery Warehouse theo kiến trúc phân lớp dữ liệu hiện đại gồm 28 bảng phân chia như sau:

| Tầng Dữ Liệu | Tên Bảng (BigQuery Dataset: `sentiment_platform`) | Vai Trò & Mô Tả |
|---|---|---|
| **Layer 0: Config** | `keyword_config` | Lưu danh sách từ khóa tìm kiếm để phát hiện video liên quan. |
| | `channel_config` | Lưu cấu hình kênh YouTube theo dõi, trạng thái crawl lịch sử. |
| | `video_crawl_state` | Tracking vòng đời video (`new` -> `growing` -> `mature` -> `archived`). |
| | `quota_daily_summary` | Tổng hợp hạn mức và lượng quota YouTube API tiêu thụ trong ngày. |
| | `quota_operation_log` | Nhật ký chi tiết từng tác vụ gọi API tiêu thụ quota. |
| | `product_config` | Cấu hình định danh sản phẩm chuẩn (`product_id`). |
| | `product_aliases` | Từ điển map từ khóa thô/slang/tên viết tắt về `product_id` chuẩn. |
| | `product_details` | Chứa thông tin mô tả chi tiết, specs của sản phẩm chuẩn. |
| | `product_spec_templates`| Template thông số kỹ thuật theo từng ngành hàng (phone, laptop). |
| | `product_resolution_candidates` | Hàng đợi các target mơ hồ cần LLM hoặc Admin gán tay. |
| | `product_detail_change_requests` | Phiếu đề xuất chỉnh sửa thông tin/specs sản phẩm do User gửi lên. |
| | `video_product_overrides` | Các cấu hình ghi đè sản phẩm được nhắc đến cho cấp video. |
| | `sentence_product_target_overrides` | Các cấu hình ghi đè target sản phẩm cho cấp câu bình luận. |
| **Layer 1: Raw** | `raw_videos` | External Table trỏ trực tiếp đến tệp NDJSON chứa video thô trên GCS. |
| | `raw_comments` | External Table trỏ trực tiếp đến tệp NDJSON bình luận thô trên GCS. |
| | `raw_comments_api` | Bảng native lưu trữ bình luận thu thập qua YouTube API (chứa timestamp chuẩn). |
| | `raw_sentiment_results` | Kết quả phân tích aspect & sentiment thô từ NLP Engine. |
| | `api_comment_backfill_state` | Lưu trạng thái checkpoint của backfill API comments cho từng video. |
| **Layer 2: Staging** | `stg_youtube_videos` | Làm sạch, ép kiểu và loại bỏ trùng lặp metadata video. |
| | `stg_youtube_comments` | Union dữ liệu comments từ scraper và API, tính toán điểm chất lượng. |
| **Layer 3: Intermediate** | `int_comment_sentences` | Tách câu tự động (native SQL) và chuẩn hóa teen code/từ lóng qua JS UDF. |
| | `int_sentiment_results` | Làm sạch và chuẩn hóa nhãn kết quả sentiment từ NLP Raw. |
| | `int_video_product_mentions` | Xác định các sản phẩm được đề cập trực tiếp trong video metadata. |
| | `int_sentence_product_targets` | Liên kết và định vị chính xác thực thể sản phẩm được đánh giá trong câu. |
| | `int_product_resolution_candidates` | Tổng hợp các candidate target cần được xử lý phân giải. |
| **Layer 4: Marts** | `dim_products` | Bảng chiều sản phẩm chuẩn dùng để truy vấn catalog và specs. |
| | `fact_product_mentions` | Bảng sự kiện lưu vết từng câu đánh giá cảm xúc đã map sản phẩm chuẩn. |
| | `agg_daily_product_ranking` | Bảng tổng hợp xếp hạng sản phẩm hằng ngày (Bayesian Score, Controversy). |
| | `causal_events` | Lưu trữ các sự kiện đột biến cảm xúc kèm video viral tương quan & lý do. |

---

## 🧠 NLP Hybrid Pipeline (Xử lý Ngôn ngữ Tự nhiên Lai)

### 1. Kiến trúc Mô hình Học sâu Cục bộ
Hệ thống sử dụng các mô hình học máy được tinh chỉnh (fine-tuned) và chạy suy luận offline cục bộ trên GPU/CPU:
- **vELECTRA Base (Aspect Extraction)**: Dựa trên kiến trúc `vielectra-base-discriminator` cho tác vụ Token Classification. Tiền xử lý tách âm tiết và align nhãn BIO bằng `underthesea.word_tokenize`. Đạt **Entity F1-score ~0.90** trên tập validation.
- **PhoBERT v2 (Sentiment Classification)**: Dựa trên kiến trúc `phobert-base-v2` cho tác vụ Sequence Classification. Tiền xử lý tách từ bằng `pyvi` (`ViTokenizer`). Format input ghép dạng: `aspect </s> sentence`. Đạt **Macro F1-score ~0.804** trên tập validation.

### 2. Cơ chế Confidence-Routing (Định tuyến Tin cậy)
Nhằm đạt sự cân bằng giữa chi phí API đám mây và độ chính xác phân tích, hệ thống áp dụng cơ chế định tuyến:
- Đối với mỗi câu bình luận, NLP Runner chạy vELECTRA để lấy nhãn khía cạnh và độ tin cậy ($C_{ner}$), chạy PhoBERT để lấy nhãn cảm xúc và độ tin cậy ($C_{sent}$).
- **Nhãn `NONE` đặc biệt**: Nếu vELECTRA phân loại aspect là `NONE` (không chứa khía cạnh sản phẩm nào), hệ thống tự động gán sentiment là `neutral` và chấp nhận kết quả mà không cần gọi PhoBERT, tối ưu hiệu năng.
- **Quyết định định tuyến**:
  - Nếu $\min(C_{ner}, C_{sent}) \ge 0.70$: Kết quả được chấp nhận trực tiếp từ mô hình cục bộ.
  - Nếu $\min(C_{ner}, C_{sent}) < 0.70$: Câu bình luận được chuyển tiếp vào hàng đợi fallback, gom lô gửi sang **Gemini Flash API** xử lý bằng Few-shot Prompt có cấu trúc.
- **Ghi kết quả**: Kết quả sau khi tích hợp được ghi nhận vào BigQuery thông qua lệnh `MERGE` dựa trên mã băm MD5 `result_id` để tránh trùng lặp dữ liệu.

### 3. Đánh Giá Hiệu Năng Thực Nghiệm (Đo trên 50K câu)

| Phương pháp tiếp cận | Accuracy | Macro F1-score | Chi phí API (với 50K câu) | Thời gian xử lý (50K câu) |
|---|:---:|:---:|:---:|:---:|
| **Chỉ dùng PhoBERT (Local)** | 78.2% | 0.742 | \$0 | ~15 phút (GPU local) |
| **Chỉ dùng Gemini Flash** | 86.5% | 0.852 | ~\$3.75 | ~30 phút (hạn chế RPM) |
| **Mô hình Lai (Hybrid - Ngưỡng 0.70)** | **85.1%** | **0.835** | **~$0.22** (giảm 94% chi phí) | **~17 phút** |

---

## 📈 Analytics Engine (Bộ Phân tích Chuyên sâu)

### 1. Bayesian Sentiment Ranking
Hệ thống sử dụng **Điểm trung bình Bayesian (Bayesian Average Score)** để triệt tiêu thiên kiến đối với sản phẩm có quá ít lượt đánh giá:

$$S_B = \frac{C \cdot m + \sum w_i \cdot s_i}{C + n}$$

Trong đó:
- $C$: Prior strength (Độ mạnh tiên nghiệm), cấu hình thực tế bằng $50.0$.
- $m$: Điểm cảm xúc trung bình toàn cầu (Global Mean Sentiment) trong 30 ngày gần nhất.
- $n$: Tổng số lượt nhắc đến (mentions) có chứa aspect của sản phẩm hiện tại.
- $s_i$: Điểm cảm xúc từng câu ($+1.0$ cho Positive, $-1.0$ cho Negative, $0.0$ cho Neutral).
- $w_i$: Trọng số cảm xúc (mặc định = 1.0).

### 2. Chỉ số Tranh cãi (Controversy Index)
Chỉ số tranh cãi đo mức độ bất đồng ý kiến của cộng đồng mạng đối với sản phẩm:

$$CI = \frac{\sigma_s}{\mu_s + 0.1}$$

Trong đó:
- $\sigma_s$: Độ lệch chuẩn của điểm cảm xúc ($STDDEV\_POP(sentiment\_score)$).
- $\mu_s$: Giá trị trung bình tuyệt đối của điểm cảm xúc ($\mid AVG(sentiment\_score) \mid$).
- Phân loại:
  - $CI > 0.6$: Tranh cãi **Cao** (Badge đỏ).
  - $0.3 \le CI \le 0.6$: Tranh cãi **Trung bình** (Badge vàng).
  - $CI < 0.3$: Tranh cãi **Thấp/Nhất quán** (Badge xanh).

### 3. Correlation Attribution Engine dùng thuật toán PELT
Để giải thích sự biến động đột ngột về mặt cảm xúc của sản phẩm trên chuỗi thời gian, công cụ Attribution thực hiện:
1. **Change Point Detection**: Nội suy chuỗi thời gian và chạy thuật toán **PELT (Pruned Exact Linear Time)** qua thư viện `ruptures` (RBF model, penalty=3.0) để tìm các điểm thay đổi cấu trúc cảm xúc có biên độ biến động $> 0.25$.
2. **Attribution Score**: Quét toàn bộ video thuộc sản phẩm có tương tác lớn trong cửa sổ $[D-7, D+7]$ ngày và tính điểm tương quan:
   $$Attribution\_Score = Temporal\_Proximity \times 0.5 + Direction\_Alignment \times 0.5$$
3. **LLM Explanation**: Chọn video có điểm tương quan cao nhất và gom 5 comment tiêu biểu gửi sang Gemini Flash để sinh câu giải thích ngữ cảnh tiếng Việt lưu vào bảng `causal_events`.

---

## 🔄 YouTube API Comment Backfill

Scraper bình luận thô có nhược điểm là trường `published_at` có thể bị sai lệch (do timestamp suy diễn từ thời gian tương đối). Nhánh API Backfill giải quyết triệt để vấn đề này:
- **PublishedAt chuẩn**: Sử dụng YouTube Data API `commentThreads.list` để lấy chính xác timestamp `snippet.publishedAt` cho các comment.
- **Quota Management**: Quản lý chặt chẽ thông qua `QuotaBudget` (bucket `youtube_api_comments`), kiểm tra quota đã dùng trong ngày từ bảng logs `quota_operation_log` (1 page = 1 unit).
- **Data Integration**: Kết quả lưu vào native table `raw_comments_api`. Mô hình dbt `stg_youtube_comments` sẽ union hai nguồn dữ liệu và ưu tiên bản ghi từ API Backfill hơn khi trùng `comment_id`.

---

## ⚙️ Yêu cầu Hệ thống & Cài đặt

Dự án tối ưu để chạy cục bộ (RAM khuyến nghị >= 16GB, có GPU Nvidia là lợi thế).

### 1. Cài đặt Môi trường
```powershell
# Clone và truy cập project
git clone <repository-url>
cd Social_media_sentiment_pipeline

# Khởi tạo conda environment
conda create -n etl-py313 python=3.13
conda activate etl-py313

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Thiết lập File `.env` ở Thư mục Gốc
```env
GCP_PROJECT_ID=your_gcp_project_id
GCS_BUCKET_NAME=product-sentiment-raw-1806
BQ_DATASET=sentiment_platform
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/your/service_account.json
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY=your_gemini_api_key
POSTGRES_URL=postgresql://user:pass@localhost:5432/web_app
JWT_SECRET_KEY=your_jwt_secret_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Cấu trúc Docker Services
Nếu muốn chạy các dịch vụ hỗ trợ (Airflow, Redis, PostgreSQL) bằng Docker Compose từ root:
```powershell
docker compose --env-file .env -f docker/docker-compose.yml up airflow-webserver airflow-scheduler redis web-db
```

---

## 🚀 Hướng dẫn Chạy Dự án Từng Bước

### Bước 0: Khởi tạo Schema
Chạy các script tạo cấu hình bảng và external tables trên BigQuery:
```powershell
conda activate etl-py313
python -m schema.run_all
python schema\layer_1_raw\init_api_comment_tables.py
python -m schema.migrate_product_catalog
```

### Bước 1: Thu thập Dữ liệu Video Raw (Scraper)
```powershell
python -m elt.main --mode full
```

### Bước 2: Tạo Candidate Video & Chạy API Comment Backfill
Để lấy chính xác timestamp bình luận của các video liên quan đến sản phẩm:
```powershell
# Chạy dbt tạo candidate videos
python scripts\dbt\dbt_runner.py run --select stg_youtube_videos int_video_product_mentions

# Chạy dry-run kiểm tra quota & candidate
python scripts\run_api_comment_backfill.py --max-videos 10 --max-comments-per-video 100 --dry-run

# Chạy backfill thật
python scripts\run_api_comment_backfill.py --max-videos 10 --max-comments-per-video 100
```

### Bước 3: Rebuild Comments và Tách Câu
```powershell
python scripts\dbt\dbt_runner.py run --select stg_youtube_comments
python scripts\dbt\dbt_runner.py run --select int_comment_sentences --full-refresh
```

### Bước 4: Chạy NLP Pipeline (Inference)
```powershell
# Chạy inference NLP
python -m nlp.runner --limit 500

# Phân giải các target mơ hồ
python -m nlp.product_target_resolver --limit 100
```

### Bước 5: Rebuild Target & Marts Ranking
```powershell
python scripts\dbt\dbt_runner.py run --select int_sentiment_results int_sentence_product_targets fact_product_mentions agg_daily_product_ranking
```

### Bước 6: Chạy Analytics PELT Attribution
```powershell
python -m analytics.pelt_attribution
```

### Bước 7: Khởi động Web App & API
1. Khởi động Backend FastAPI:
```powershell
conda activate etl-py313
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# (Tùy chọn) Seed tài khoản admin demo: python -m api.seed_admin
```
Swagger UI xem tại: `http://localhost:8000/docs`

2. Khởi động Frontend Next.js:
```powershell
cd frontend
npm install
npm run dev
```
Trang chủ ứng dụng chạy tại: `http://localhost:3000`

---

## 🛠 Hướng dẫn Debug (Troubleshooting)

- **Lỗi hiển thị Dashboard rỗng/Thiếu dữ liệu**: Đi qua checklist sau:
  1. Kiểm tra bảng `raw_comments_api` có dữ liệu chưa.
  2. Đảm bảo chạy `stg_youtube_comments` để tích hợp dữ liệu API.
  3. Kiểm tra đã chạy `int_comment_sentences` với tham số `--full-refresh` chưa.
  4. Xác nhận `raw_sentiment_results` đã được cập nhật kết quả NLP từ `nlp.runner`.
  5. Đảm bảo đã chạy các marts dbt để refresh dữ liệu ranking.
  6. Xóa cache Redis hoặc đợi hết TTL 300s.
- **Lỗi Region BigQuery**: Đảm bảo trong `transform/profiles.yml` đã thiết lập `location: asia-southeast1` giống với location của Dataset gốc và GCS bucket. Nếu không dbt sẽ tạo bảng ở US và báo lỗi không tương thích location.
- **Lỗi Rate Limit API/Proxy**: Nếu gặp lỗi HTTP 429 liên tục khi crawl comment scraper, kiểm tra kết nối BrightData credentials trong `.env` đã chính xác chưa.

---

## 🔄 Cấu trúc Điều phối của Apache Airflow
Quy trình tự động hóa được chia nhỏ thành 4 DAGs chạy tuần tự thông qua cơ chế Sensor và Trigger:
1. **`seed_sync_dag`**: Tự động đồng bộ các file cấu hình CSV (`seed_products.csv`, `channel_config`, v.v.) lên BigQuery.
2. **`youtube_daily_extraction_dag`**: Kích hoạt lúc 2:00 AM UTC+7 hằng ngày. Tiến hành chạy Daily Scan, Historical Scan (nếu có kênh mới), Comment Crawl và dbt transformation lớp Staging/Intermediate.
3. **`sentiment_analysis_dag`**: Kích hoạt sau DAG extraction. Gọi NLP Runner suy luận aspect/sentiment cho các câu mới và thực hiện BQ MERGE.
4. **`analytics_dag`**: Kích hoạt cuối cùng để tính toán Bayesian ranking, chạy PELT attribution phân tích đột biến và refresh toàn bộ Marts layer.

---
*Developed by Khoa Trần (2026)*
---
