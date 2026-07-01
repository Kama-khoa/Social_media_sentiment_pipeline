**SENTIMENT INTELLIGENCE PLATFORM**

## Cập Nhật Thực Thi 2026-06-02

Hệ thống đã mở rộng từ ranking dựa trên keyword sang catalog sản phẩm chuẩn:

- `keyword_config` chỉ còn dùng để discovery video. `dim_products` đọc từ `product_config`.
- Catalog seed độc lập tại `elt/seed_data/seed_products.csv`, gồm 500 sản phẩm mẫu thuộc điện thoại, laptop và tai nghe.
- dbt đã bổ sung `int_video_product_mentions`, `int_sentence_product_targets` và `int_product_resolution_candidates`.
- `nlp.product_target_resolver` dùng alias trước, LLM fallback sau; candidate còn mơ hồ chờ Admin xử lý.
- Ranking tổng hợp theo `product_id` chuẩn. Trang chi tiết trả thêm `product_details` và specs theo template category.
- User đăng nhập được gửi `product_detail_change_requests`; chỉ Admin được duyệt và merge dữ liệu vào `product_details`.
- FastAPI + Next.js đã có analytics pages, CRUD keyword/channel, Pipeline Health và trang Admin Products.
- Auth store hiện dùng PostgreSQL qua SQLAlchemy. Redis cache áp dụng cho endpoint đọc analytics.

Trạng thái cần xử lý trước production:

1. Bật lại Phase A daily scan trong `elt.main` sau khi xác nhận quota seed production.
2. Chuyển truy vấn viral video của `PELTAttribution._query_videos_in_window()` từ mapping legacy `video_crawl_state.keyword_id` sang `int_video_product_mentions`.
3. Rebuild lịch sử `fact_product_mentions`, ranking và `causal_events` sau migration catalog.

Chi tiết catalog và moderation: [`product-catalog-and-moderation.md`](product-catalog-and-moderation.md).

---

## Cập Nhật Thực Thi 2026-05-30

Giai đoạn NLP đã hoàn chỉnh ở mức vận hành:

- PhoBERT sentiment đã được fine-tune và đưa về local tại `models/phobert_sentiment`, macro F1 validation khoảng `0.804`.
- vELECTRA aspect extraction đã được fine-tune trên boundary dataset và đưa về local tại `models/velectra_aspect`, entity F1 khoảng `0.90`.
- `ConfidenceRouter` dùng threshold `0.70`; debug 500 sentences cho fallback tổng `6.0%`.
- `nlp.runner` chạy batch inference từ `int_comment_sentences`, hỗ trợ debug/dry-run/reprocess, và upsert vào `raw_sentiment_results` bằng BigQuery MERGE.
- dbt đã nối kết quả NLP vào `int_sentiment_results` và `fact_product_mentions`.

Kế hoạch còn lại của dự án chuyển trọng tâm sang Phase 4 Analytics:

1. Populate thêm dữ liệu NLP đủ lớn.
2. Hoàn thiện Bayesian ranking và controversy index trên `fact_product_mentions`.
3. Hoàn thiện PELT attribution và bảng causal events.
4. Sau analytics mới chuyển sang xây dựng web app FastAPI + Next.js.

---

Nền tảng Phân tích Cảm xúc Sản phẩm Công nghệ từ YouTube

*Kế hoạch Triển khai Chi tiết — Đồ án Tốt nghiệp 2026*

| **Sinh viên** | Trần Minh Khoa — Khoa CNTT, Trường ĐH Công nghệ GTVT |
|----|----|
| **Giảng viên HD** | ThS. Khuất Thị Ngọc Ánh |
| **Thời gian** | 01/03/2026 – 24/05/2026 \| 12 Tuần \| 120–180 giờ thực tế |
| **Phần cứng** | GTX 1650 4GB \| i5-11th Gen \| 16GB RAM |
| **Ngân sách** | **\$35 – \$60 (toàn bộ dự án)** |

#  TỔNG QUAN DỰ ÁN

### Mô tả tổng thể

Sentiment Intelligence Platform là hệ thống end-to-end thu thập bình
luận YouTube về sản phẩm công nghệ Việt Nam (smartphone, laptop, tai
nghe, thiết bị nhà thông minh), chạy qua pipeline NLP Hybrid gồm
vELECTRA + PhoBERT fine-tuned kết hợp Gemini Flash làm fallback, và cuối
cùng trình bày kết quả phân tích qua một web app thống nhất cho hai
actor: Guest/User và Admin.

### Kiến trúc luồng dữ liệu tổng thể

- Ingestion: Ưu tiên chạy thủ công trong Conda `etl-py313`; Airflow DAG
  dùng để orchestration. Phase B historical dùng yt-dlp, Phase C comment
  backlog dùng youtube-comment-downloader. Phase A daily dùng YouTube API
  `search.list` theo kênh nhưng hiện đang tạm comment trong `elt.main`.

- Storage: File JSON thô lưu trên Google Cloud Storage theo phân vùng
  YYYY/MM/DD.

- Transformation: dbt xử lý 3 lớp ELT — Staging (làm phẳng JSON),
  Intermediate (chuẩn hóa, NLP promote và resolve target sản phẩm),
  Marts (dimension, fact và ranking theo `product_id` chuẩn).

- NLP Pipeline: vELECTRA trích xuất khía cạnh (Token Classification) +
  PhoBERT phân loại cảm xúc (Sequence Classification) +
  Confidence-Routing chuyển sang Gemini khi confidence \<= 0.70.

- Analytics: Bayesian Ranking, Controversy Index, Correlation
  Attribution Engine dùng thuật toán PELT (ruptures).

- Application: một Next.js web app gọi FastAPI + Redis Cache, hỗ trợ
  Guest/User tra cứu insight và gửi phiếu bổ sung specs; Admin quản lý
  cấu hình crawl, catalog sản phẩm, candidate resolution, phiếu chỉnh
  sửa và theo dõi health của Airflow pipeline.

### Các điểm nhấn quan trọng mang tính quyết định

| **\#** | **Điểm quyết định** | **Lý do quan trọng** |
|:--:|----|----|
| **1** | **Zero-Quota Ingestion** | Thay toàn bộ comment API bằng youtube-comment-downloader (0 quota). Đây là điều kiện tiên quyết để pipeline có thể chạy bền vững hàng ngày với 26+ kênh và 100+ keywords mà không bị chặn. |
| **2** | **Colab Training thay Local GPU** | GTX 1650 chỉ có 4GB VRAM — không đủ để fine-tune PhoBERT + vELECTRA song song. Bắt buộc phải dùng Google Colab (T4 16GB) để hoàn thành đúng tiến độ tuần 7. |
| **3** | **Knowledge Distillation — Auto-Annotation** | Dùng Gemini API gán nhãn tự động 2,000 câu thay vì gán tay. Quyết định này tiết kiệm 4 tuần nhân công và là nền tảng của toàn bộ pipeline NLP. |
| **4** | **Confidence-Routing Threshold 0.70** | Ngưỡng 0.70 được chọn sau debug local 500 sentences, giúp giữ fallback tổng khoảng 6% và giảm chi phí Gemini nhưng vẫn route các case mơ hồ. |
| **5** | **Historical Data — Tuần 1 bắt buộc** | Toàn bộ Phase 4 Correlation Attribution Engine phụ thuộc vào chuỗi thời gian đủ dài. Nếu không crawl historical data ngay tuần 1, Phase 4 sẽ không có dữ liệu để phân tích. |
| **6** | **BrightData Proxy cho Comment Downloader** | youtube-comment-downloader có thể bị YouTube rate-limit. BrightData Residential Proxy là giải pháp đã được xác nhận trong ngân sách dự án để đảm bảo thu thập ổn định. |
| **7** | **Tách keyword discovery khỏi product catalog** | Keyword crawl như `review` hoặc `samsung` không phải sản phẩm. Catalog chuẩn, alias và resolver target đảm bảo ranking hiển thị model đầy đủ và gom sentiment đúng sản phẩm. |

#  CÁC BƯỚC CẦN XÉT DUYỆT VÀ CHUẨN BỊ SỚM

Các hạng mục dưới đây yêu cầu thời gian xét duyệt từ bên ngoài hoặc phụ
thuộc vào dịch vụ của bên thứ ba. Cần hoàn thành TRƯỚC KHI bắt đầu code
để tránh bị chặn giữa chừng.

### 1. Đăng ký và cấu hình GCP (Google Cloud Platform)

Thời gian xét duyệt ước tính: 1–3 ngày (xác minh tài khoản thanh toán).

- Truy cập console.cloud.google.com và tạo Project mới với tên phù hợp.

- Bật các API cần thiết: YouTube Data API v3, BigQuery API, Cloud
  Storage API.

- Tạo Service Account với role BigQuery Admin và Storage Admin, tải file
  JSON credentials về máy.

- Kích hoạt Google Cloud Storage: tạo bucket tên
  'product-sentiment-raw-1806' với region asia-southeast1.

- Kích hoạt BigQuery: tạo dataset 'sentiment_platform'.

- Lưu ý: tài khoản mới được \$300 credit miễn phí 90 ngày — đủ cho toàn
  bộ thesis.

- Tài liệu tham khảo:
  https://cloud.google.com/docs/authentication/getting-started

### 2. Đăng ký Gemini API Key

Thời gian: Tức thì (không cần xét duyệt).

- Truy cập aistudio.google.com và đăng nhập bằng tài khoản Google.

- Tạo API Key mới, lưu vào file .env với tên biến GEMINI_API_KEY.

- Kiểm tra giới hạn free tier: 1,500 requests/ngày và 1 triệu token/phút
  — đủ cho thesis.

- Tài liệu: https://ai.google.dev/gemini-api/docs

### 3. Đăng ký BrightData Residential Proxy

Thời gian xét duyệt: 1–2 ngày (xác minh tài khoản và nạp tiền).

- Truy cập brightdata.com, đăng ký tài khoản và chọn gói Residential
  Proxy.

- Nạp tối thiểu \$15–20 để đủ cho toàn bộ quá trình thu thập comment
  (ước tính 2–4GB traffic).

- Tạo proxy zone, lấy thông tin host, port, username và password để cấu
  hình vào youtube-comment-downloader.

- Lưu ý: cần xác minh danh tính bằng email và đôi khi cần xác minh thẻ
  ngân hàng.

- Tài liệu: https://docs.brightdata.com/proxy-networks/residential

### 4. Thiết lập Google Colab cho việc huấn luyện mô hình

Thời gian: Không cần xét duyệt nhưng cần chuẩn bị dữ liệu và môi trường
trước tuần 7 ít nhất 3 ngày.

- Truy cập colab.research.google.com, kiểm tra kết nối GPU T4 bằng lệnh
  nvidia-smi.

- Nếu GPU T4 không khả dụng trong free tier, cân nhắc Colab Pro
  (\$10/tháng) để đảm bảo GPU trong suốt quá trình training.

- Kết nối Google Drive để lưu checkpoint và dataset: from google.colab
  import drive.

- Chuẩn bị sẵn file requirements_colab.txt riêng biệt với
  requirements.txt của ETL.

- Tài liệu: https://colab.research.google.com/notebooks/gpu.ipynb

### 5. Cài đặt môi trường Local (Conda etl-py313)

Thời gian: 1–2 giờ cài đặt lần đầu.

- Cài đặt Miniconda/Anaconda trên Windows.

- Tạo môi trường ảo với Python 3.13: `conda create -n etl-py313 python=3.13`

- Kích hoạt môi trường và cài đặt thư viện: `conda activate etl-py313` và `pip install -r requirements.txt`.

- (Tùy chọn cho Production sau này) Cài Docker Desktop for Windows nếu muốn chạy Airflow qua Docker. Tuy nhiên, trong giai đoạn dev, sẽ ưu tiên chạy script ETL và dbt thủ công (manual) qua môi trường Conda để tránh overload hệ thống.

#  GIAI ĐOẠN 1 — DATA INGESTION (Tuần 1–3)

Mục tiêu: Xây dựng luồng thu thập dữ liệu tự động hoàn toàn không phụ
thuộc giới hạn YouTube API Quota, lưu trữ JSON thô lên Google Cloud
Storage phân vùng theo ngày, đảm bảo đủ dữ liệu lịch sử cho Phase 4
Analytics.

### Tuần 1 — Setup hệ thống và Historical Crawl

**Các bước thực hiện**

1.  Hoàn thiện toàn bộ cấu hình GCP đã chuẩn bị từ mục trên: kiểm tra
    kết nối service account, thử upload file test lên GCS qua định dạng NDJSON.

2.  Cài đặt Conda, tạo môi trường `etl-py313` và nạp các biến môi trường vào file `.env`.

3.  Thiết lập schema khởi tạo trên BigQuery: chạy các script trong folder `schema/` để tạo các bảng cấu hình và External Tables (layer 0 và layer 1).

4.  Thực thi script chạy pipeline thủ công: `conda run -n etl-py313 python -m elt.main --mode full`.
    Entry point hiện chạy Phase B (Historical) và Phase C (Backlog).
    Phase A (Daily) đã có implementation nhưng đang tạm comment để kiểm
    soát quota trong development.

5.  Kiểm tra kết quả: xác nhận file NDJSON xuất hiện trên GCS theo cấu
    trúc raw/videos/YYYY/MM/DD/ và raw/comments/YYYY/MM/DD/.

**Công cụ sử dụng**

- yt-dlp: lấy metadata video (tiêu đề, lượt xem, thống kê) với 0 YouTube
  API quota.

- YouTube Data API v3 `search.list`: discovery video mới theo từng kênh
  cho Phase A khi được bật lại.

- Google Cloud Storage Python SDK (google-cloud-storage): upload file
  JSON.

- Docker Desktop + Docker Compose: tùy chọn cho triển khai Airflow sau
  này; development hiện ưu tiên chạy local/manual trong Conda.

**Tài liệu tham khảo**

- yt-dlp documentation: https://github.com/yt-dlp/yt-dlp#readme

- GCS Python Client:
  https://cloud.google.com/storage/docs/reference/libraries

- Airflow local/manual runtime và Docker Compose tùy chọn:
  https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html

### Tuần 2 — Viết Hybrid Extractor theo OOP

**Các bước thực hiện**

6.  Viết `extract/base_extractor.py` với Abstract Base Class định nghĩa các interface chuẩn.

7.  Implement các lớp trích xuất dữ liệu chia theo đối tượng: `VideoExtractor` (search.list và yt-dlp flat extract) và `CommentExtractor` (youtube-comment-downloader với cơ chế retry).

8.  Sử dụng Data Transfer Objects (DTO) như `VideoDTO`, `CommentDTO` trong `elt/datacontext/models/` để chuẩn hóa cấu trúc dữ liệu.

9.  Thiết lập `GCSClient` trong `datacontext/gcs_client.py` để tự động unroll danh sách dict và lưu thành chuẩn **NDJSON** khi upload lên bucket.

10. Viết unit test hoặc chạy log debug để xác nhận hệ thống lấy đúng metadata và bypass được rate-limit nhờ BrightData Proxy.

**Công cụ sử dụng**

- youtube-comment-downloader \>= 0.1.78: thu thập bình luận với 0
  YouTube API quota.

- YouTube Data API v3: `search.list` theo kênh cho Phase A daily.

- yt-dlp: lấy metadata video.

- BrightData Residential Proxy: đảm bảo thu thập ổn định không bị block.

- Python ABC (abstract base class): thiết kế OOP Template Method
  Pattern.

**Tài liệu tham khảo**

- youtube-comment-downloader:
  https://github.com/egbertbouman/youtube-comment-downloader

- Python ABC: https://docs.python.org/3/library/abc.html

- BrightData docs:
  https://docs.brightdata.com/proxy-networks/residential

### Tuần 3 — Airflow DAG Automation

**Các bước thực hiện**

11. Tạm thời chạy pipeline thủ công qua script (manual execution) thay vì Airflow Docker để tiết kiệm tài nguyên. Quản lý trạng thái xử lý bằng các bảng tracking trên BigQuery (`video_crawl_state`).

12. Thiết kế `QuotaBudget` class trong `elt/` để theo dõi YouTube API quota (10,000 units/ngày), đảm bảo không bao giờ vượt giới hạn.

13. Tổ chức luồng chạy `elt/main.py` thành 3 pha: Phase A (Daily scan qua API), Phase B (Historical qua yt-dlp), Phase C (Backlog crawl comments).

14. Cập nhật `seed_loader.py` để đồng bộ channel, keyword discovery,
    catalog chuẩn từ `seed_products.csv`, alias và template specs lên
    BigQuery.

15. Xác nhận dữ liệu được ghi đè ổn định trên GCS (GCS-first) và sau đó commit trạng thái thành công lên BigQuery (BQ-second).

**Công cụ sử dụng**

- Apache Airflow: DAG, BashOperator, sensor và REST API `/api/v1`.
  Development hiện ưu tiên chạy script thủ công trong Conda; Docker là
  tùy chọn triển khai sau.

- Google Cloud Storage: lưu trữ JSON thô phân vùng theo ngày.

- BigQuery (google-cloud-bigquery): lưu log quota và trạng thái crawl
  vào các bảng tracking.

**Tài liệu tham khảo**

- Airflow fundamentals:
  https://airflow.apache.org/docs/apache-airflow/stable/tutorial/fundamentals.html

- Airflow best practices:
  https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html

- GCS object naming: https://cloud.google.com/storage/docs/objects

**Schema BigQuery cần tạo cho Phase 1**

- channel_config: thông tin 26+ kênh YouTube Việt Nam (channel_id, tên,
  subscriber, is_historically_scanned).

- keyword_config: danh sách 100 keywords nhóm theo semantic cluster.

- product_config, product_aliases, product_details và
  product_spec_templates: catalog chuẩn và specs có thể bổ sung dần.

- product_resolution_candidates, product_detail_change_requests,
  video_product_overrides và sentence_product_target_overrides: hàng
  chờ và audit cho resolve target, moderation.

- video_crawl_state: theo dõi trạng thái từng video
  (new/growing/mature/archived).

- quota_daily_summary và quota_operation_log: log sử dụng API quota theo
  ngày.

#  GIAI ĐOẠN 2 — DATA TRANSFORMATION (Tuần 4–5)

Mục tiêu: Dùng dbt biến đổi dữ liệu thô JSON từ Data Lake thành các bảng
SQL có cấu trúc chuẩn trong BigQuery theo kiến trúc 3 lớp ELT (Staging →
Intermediate → Marts), đảm bảo dữ liệu sạch 100% trước khi đưa vào NLP
pipeline.

### Tuần 4 — dbt Setup và Staging Models

**Các bước thực hiện**

17. Cấu hình file `profiles.yml` để kết nối BigQuery. Chú ý đặt `location: asia-southeast1` để đồng bộ với dataset của Data Lake.

18. Xác nhận External Tables (tạo ở Phase 1) có thể đọc dữ liệu định dạng **NDJSON** từ GCS thành công.

19. Viết model `stg_youtube_videos`: dùng JSON_EXTRACT để flatten metadata video (video_id, title, channel_id, view_count, etc.).

20. Viết model `stg_youtube_comments`: dùng UNNEST/JSON_EXTRACT để flatten mảng bình luận, thêm các trường parent_comment_id và is_reply flag.

21. Viết logic SQL tính `data_quality_score`: trừ điểm nếu comment chứa URL, < 5 ký tự, hoặc toàn emoji (score < 0.5 bị đánh dấu là spam).

22. Chạy dbt thủ công qua file `run_dbt.bat` (Windows) hoặc `conda run -n etl-py313 python scripts/dbt/dbt_runner.py run`. Kiểm tra kết quả trên BigQuery.

**Công cụ sử dụng**

- dbt-bigquery 1.7+: framework SQL transformation, model
  materialization, ref() và source().

- BigQuery External Table: kết nối GCS JSON không cần import.

- BigQuery SQL: JSON_EXTRACT, UNNEST, DATE partition,
  GENERATE_SURROGATE_KEY.

**Tài liệu tham khảo**

- dbt fundamentals (free course, hoàn thành trong 4 ngày):
  https://courses.getdbt.com/courses/fundamentals

- BigQuery External Tables:
  https://cloud.google.com/bigquery/docs/external-tables

- BigQuery JSON functions:
  https://cloud.google.com/bigquery/docs/reference/standard-sql/json_functions

### Tuần 5 — Intermediate Models và Data Quality Testing

**Các bước thực hiện**

23. Chuẩn bị file vn_slang_dictionary.csv chứa mapping từ lóng tiếng
    Việt: sdt→số điện thoại, cam→camera, ko→không, pin→pin. Chạy dbt
    seed để nạp vào BigQuery.

24. Viết model int_comment_sentences: tách câu dài thành nhiều câu ngắn
    độc lập, chuẩn hóa teen code dựa trên từ điển vn_slang, detect ngôn
    ngữ cơ bản (tiếng Việt vs tiếng Anh).

25. Viết dbt test với not_null constraint cho comment_id và video_id,
    unique constraint để loại duplicate, accepted_values cho các trường
    phân loại.

26. Chạy dbt test, xác nhận 100% test pass trước khi chuyển sang Phase
    3.

27. Chạy dbt docs generate && dbt docs serve để xuất Data Lineage Graph,
    chụp ảnh để đưa vào báo cáo.

28. Viết dbt model int_sentiment_results với schema sẵn sàng nhận kết
    quả từ NLP pipeline (tuần 8 sẽ populate data thực).

28a. Bổ sung `int_video_product_mentions`, `int_sentence_product_targets`
    và `int_product_resolution_candidates`. Match alias trong
    title/description/comment trước; target mơ hồ chờ LLM hoặc Admin.

28b. Chuyển `dim_products` sang đọc `product_config`. Không dùng
    `keyword_id` làm `product_id`.

**Công cụ sử dụng**

- dbt seed: nạp CSV seed data vào BigQuery.

- dbt test: kiểm thử tự động data quality.

- dbt docs generate: tạo Data Lineage Graph trực quan.

- langdetect 1.0.9: phát hiện tiếng Việt vs tiếng Anh ở cấp độ câu.

**Tài liệu tham khảo**

- dbt testing guide: https://docs.getdbt.com/docs/build/data-tests

- dbt seeds: https://docs.getdbt.com/docs/build/seeds

- langdetect Python: https://pypi.org/project/langdetect/

#  GIAI ĐOẠN 3 — NLP HYBRID PIPELINE (Tuần 6–8)

Mục tiêu: Xây dựng pipeline NLP Hybrid kết hợp vELECTRA (trích xuất khía
cạnh) và PhoBERT fine-tuned (phân loại cảm xúc), với Gemini Flash làm
fallback thông minh. Áp dụng Knowledge Distillation — dùng Gemini gán
nhãn tự động thay vì gán tay 4 tuần.

### Tuần 6 — Auto-Annotation bằng Knowledge Distillation

**Các bước thực hiện**

29. Viết truy vấn BigQuery lấy ngẫu nhiên 2,000 câu bình luận sạch nhất
    từ bảng int_comment_sentences (data_quality_score = 1.0,
    is_vietnamese = True).

30. Thiết kế Prompt few-shot với 3–5 ví dụ mẫu chỉ định rõ format output
    JSON chứa entity, aspect_label (Pin/Camera/Màn hình/Hiệu năng/Thiết
    kế/Giá), segment và nhãn BIO cho từng token.

31. Viết script gửi batch 50 câu/request lên Gemini Flash API (~40
    requests tổng, nằm trong free tier).

32. Parse và validate response JSON, loại bỏ câu có output không hợp lệ.

33. Chạy script `nlp/training/prepare_dataset_v2.py` để làm sạch dữ liệu: gộp các JSON thô thành `labeled_master.jsonl`, gom nhóm theo câu (để tránh rò rỉ dữ liệu khi chia train/val), gộp nhãn trùng, validate định dạng BIO, bắt lỗi spans > 12 tokens và ghi file conflicts để review.

34. Trộn thêm 20-30% câu `NONE` thật (không chứa aspect) và chia Train/Val theo tỉ lệ 80/20 không overlap. Export thành định dạng HuggingFace (`sentiment/phobert` và `ner/velectra`).

**Công cụ sử dụng**

- Gemini Flash API: gán nhãn tự động với few-shot prompting (Brown
  et al., 2020).

- underthesea 6.8.4: word tokenization tiếng Việt — bắt buộc trước khi
  tokenize bằng PhoBERT.

- Google BigQuery Python SDK: truy vấn lấy dữ liệu mẫu.

- json Python module: parse và validate response từ Gemini.

**Tài liệu tham khảo**

- Gemini API structured output:
  https://ai.google.dev/gemini-api/docs/structured-output

- Brown et al. 2020 — Few-shot prompting: Language Models are Few-Shot
  Learners (NeurIPS 2020).

- underthesea documentation: https://underthesea.readthedocs.io/

- UIT-VSFC dataset (tham khảo thêm nhãn cảm xúc):
  https://huggingface.co/datasets/uitnlp/vietnamese_students_feedback

### Tuần 7 — Fine-tune vELECTRA và PhoBERT trên Google Colab (Tuần ML quan trọng nhất)

**Phần A — Fine-tune vELECTRA cho Aspect Extraction**

Đây là bước sử dụng trực tiếp bộ dataset NER đã được làm sạch và xuất ra từ `prepare_dataset_v2.py`. Mục tiêu là fine-tune vELECTRA để nhận diện đúng 6 khía cạnh sản phẩm ở cấp độ token.

35. Đồng bộ thư mục `dataset_hf/` lên Google Drive.
36. Load bộ dataset bằng thư viện `datasets` của HuggingFace, map các nhãn BIO sang ID.
37. Load model vELECTRA từ HuggingFace Hub bằng `AutoModelForTokenClassification.from_pretrained()`, truyền vào num_labels bằng tổng số nhãn BIO.
38. Cấu hình `DataCollatorForTokenClassification` để tự động padding và căn chỉnh nhãn với subword tokens (gán nhãn -100 cho subwords để bỏ qua khi tính loss).
39. Thiết lập `TrainingArguments`: `learning_rate=1e-5`, `batch_size=16`, `epochs=10`, `metric_for_best_model="f1"`, `early_stopping_patience=2`. Sử dụng `Trainer` mặc định (không dùng WeightedTokenTrainer để tránh False Positive trầm trọng).
40. Chạy training và quan sát loss curve. Đảm bảo model học một cách ổn định nhờ tập dataset cân bằng nhãn O.
41. Evaluate trên tập validation. Tính F1-score theo từng nhãn bằng `seqeval` — mục tiêu F1 >= 0.70 trên tập validation.
42. Spot-check kết quả và lưu model checkpoints vào Google Drive.

**Phần B — Fine-tune PhoBERT cho Sentiment Classification**

Fine-tune PhoBERT trên bộ dữ liệu Aspect-Sentiment (đã gom nhóm theo aspect-sentiment từ `prepare_dataset_v2.py`).

43. Tiền xử lý văn bản: Sử dụng `pyvi` (`ViTokenizer.tokenize`) để thực hiện tách từ tiếng Việt chuẩn trước khi tokenize bằng PhoBERT.
44. Định dạng input: Truyền `aspect` vào text_pair và `sentence` đã segmented vào text chính của tokenizer, định dạng kết quả ghép thành `aspect </s> sentence`.
45. Thiết lập `TrainingArguments`: `learning_rate=1e-5`, `batch_size=16`, `epochs=5`, `lr_scheduler_type="cosine"`, `metric_for_best_model="f1"`.
46. Sử dụng `Trainer` mặc định với `DataCollatorWithPadding` và hàm tính macro F1 cho 3 nhãn cảm xúc (tích cực, tiêu cực, trung lập).
47. Thực thi huấn luyện trên Colab GPU T4. Đọc loss curve và đảm bảo F1 score cải thiện và đạt mục tiêu >= 0.80.
48. Export model weights và tokenizer vào thư mục `phobert_sentiment/`, lưu lên Google Drive.

**Config fine-tune chi tiết**

- vELECTRA: model `FPTAI/velectra-base-discriminator-cased` hoặc `NlpHUST/vielectra-base-discriminator`, task Token Classification, dataset `ner/velectra/` (~5,000+ câu, chia 80/20), lr=1e-5, epochs=10, batch_size=16, early stopping.
- PhoBERT: model `vinai/phobert-large` hoặc `vinai/phobert-base-v2`, task Sequence Classification, dataset `sentiment/phobert/`, lr=1e-5, epochs=5, batch_size=16, early stopping.
- Dùng `seqeval` để tính F1 cho vELECTRA (NER metric chuẩn), dùng `scikit-learn` macro F1 cho PhoBERT.
- Lưu checkpoint vào Google Drive mỗi 200 steps (vELECTRA) và 500 steps (PhoBERT) để tránh mất kết quả khi Colab disconnect.

**Công cụ sử dụng**

- Google Colab (GPU T4 16GB VRAM): môi trường training cả 2 model.

- HuggingFace Transformers 4.38+: AutoModelForTokenClassification
  (vELECTRA), AutoModelForSequenceClassification (PhoBERT), Trainer,
  TrainingArguments, DataCollatorForTokenClassification.

- HuggingFace Datasets: load, split và format dataset.

- seqeval: tính F1-score theo chuẩn NER cho vELECTRA (entity-level,
  không phải token-level).

- scikit-learn: confusion matrix và classification report cho PhoBERT.

- underthesea 6.8.4: word tokenization cho vELECTRA.

- pyvi 0.1.11: tiếng Việt word segmentation cho PhoBERT.

**Tài liệu tham khảo**

- HuggingFace Token Classification guide:
  https://huggingface.co/docs/transformers/tasks/token_classification

- HuggingFace fine-tuning guide (PhoBERT):
  https://huggingface.co/docs/transformers/training

- seqeval library: https://github.com/chakki-works/seqeval

- DataCollatorForTokenClassification:
  https://huggingface.co/docs/transformers/main_classes/data_collator

- NlpHUST/vielectra-base-discriminator model card:
  https://huggingface.co/NlpHUST/vielectra-base-discriminator

- PhoBERT paper: PhoBERT: Pre-trained Language Models for Vietnamese
  (EMNLP 2020 Findings).

- UIT-VSFC dataset:
  https://huggingface.co/datasets/uitnlp/vietnamese_students_feedback

### Tuần 8 — Validate vELECTRA Output và Confidence-Routing Integration

**Các bước thực hiện**

44. Tải cả 2 bộ model weights từ Google Drive về máy local: thư mục
    velecra_aspect_extractor/ và thư mục phobert_sentiment/. Load lên bộ
    nhớ bằng from_pretrained() với đường dẫn local.

45. Validate độc lập output của vELECTRA trước khi nối pipeline: chạy
    vELECTRA trên 100 câu mẫu từ int_comment_sentences, kiểm tra các
    trường hợp biên — câu không chứa khía cạnh nào (toàn nhãn O), câu
    chứa nhiều khía cạnh cùng lúc, câu ngắn dưới 5 từ, câu chứa emoji
    hoặc số. Xác nhận model trả về segment hợp lệ trước khi đưa sang
    PhoBERT.

46. Viết hàm extract_aspect_segments(sentence) gọi vELECTRA: nhận câu
    gốc → word_tokenize bằng underthesea → tokenize bằng vELECTRA
    tokenizer → chạy inference → group các token liên tiếp cùng entity
    thành segment → trả về list các (aspect_label, segment_text). Nếu
    không có khía cạnh nào được nhận diện, trả về list rỗng và bỏ qua
    câu đó.

47. Viết hàm classify_sentiment(segment) gọi PhoBERT: nhận segment text
    từ bước trên → word_tokenize → tokenize bằng PhoBERT tokenizer →
    chạy inference → trả về {label: POS/NEG/NEU, confidence_score:
    float}.

48. Implement logic Confidence-Routing: nếu confidence_score \> 0.70 thì
    ghi kết quả PhoBERT, nếu confidence_score \<= 0.70 thì đóng gói câu
    gốc + aspect_label gửi lên Gemini Flash với prompt có context để xử
    lý lại, nhận về {label, explanation}.

49. Lưu vào bảng int_sentiment_results: comment_id, aspect_label,
    segment_text, sentiment_label, confidence_score, inference_model
    (velectra+phobert hoặc gemini), processed_at.

50. Tích hợp toàn bộ pipeline thành script chạy thủ công (hoặc tích hợp vào `sentiment_analysis_dag` khi Airflow đã cấu hình xong). Đảm bảo xử lý lỗi từng câu riêng lẻ — 1 câu lỗi không làm sập toàn bộ batch.

51. Đo lường và ghi log: tính % câu được vELECTRA nhận diện có ít nhất 1
    khía cạnh, % câu route sang Gemini do confidence thấp (mục tiêu
    70–75% xử lý hoàn toàn bằng local model), tổng thời gian xử lý mỗi
    batch.

51a. Chạy `nlp.product_target_resolver` sau lượt dbt intermediate đầu
    tiên: alias match trước, LLM fallback sau. Ghi override cho video và
    sentence target; candidate chưa chắc chắn chờ Admin xử lý.

**Công cụ sử dụng**

- PyTorch + HuggingFace Transformers: load model local và chạy
  inference.

- pyvi: word segmentation trước khi đưa vào PhoBERT (bắt buộc).

- underthesea: tokenization và alignment BIO cho vELECTRA.

- Gemini Flash API: fallback cho các câu confidence thấp và target sản
  phẩm mơ hồ.

- BigQuery MERGE theo `result_id`: checkpoint và tránh xử lý trùng kết
  quả inference.

- Apache Airflow: tích hợp vào DAG tự động.

**Tài liệu tham khảo**

- Confidence calibration trong NLP: Temperature Scaling for Deep Neural
  Networks (Guo et al., 2017).

- Gemini structured output:
  https://ai.google.dev/gemini-api/docs/structured-output

- torch.no_grad() và model.eval():
  https://pytorch.org/docs/stable/generated/torch.no_grad.html

#  GIAI ĐOẠN 4 — ANALYTICS ENGINE (Tuần 9–10)

Mục tiêu: Xây dựng hệ thống tính toán Bayesian Ranking, Controversy
Index và Correlation Attribution Engine — ba đóng góp học thuật cốt lõi
của dự án phân biệt thesis này với các hệ thống sentiment đơn giản.

### Tuần 9 — Bayesian Ranking và Controversy Index

**Các bước thực hiện**

52. Viết dbt model mart_product_ranking tính Bayesian Score theo công
    thức: (C × m + Tổng(w × s)) / (C + n), trong đó C = 50 là prior
    strength, m là sentiment trung bình toàn cục trong rolling window 30
    ngày, n là tổng số mentions, s là điểm sentiment.

53. Hiệu ứng của Bayesian Score: sản phẩm có ít mentions bị kéo về mức
    sentiment trung bình toàn cục, tránh tình trạng sản phẩm chỉ có 3
    bình luận tích cực bị xếp hạng nhất.

54. Tính Controversy Index: Std(sentiment_scores) /
    (\|Mean(sentiment_scores)\| + 0.1). Giá trị cao cho thấy sản phẩm bị
    đánh giá cực đoan (vừa rất khen vừa rất chê), giá trị thấp cho thấy
    đánh giá nhất quán.

55. Gán nhãn Controversy: icon đỏ (chỉ số \> 0.6 = tranh cãi), icon vàng
    (0.3–0.6 = trung bình), icon xanh (\< 0.3 = nhất quán).

56. Populate bảng agg_daily_product_ranking với Bayesian Score,
    Controversy Index, số mentions, top aspects theo từng ngày.

57. Kiểm tra kết quả: top 10 ranking phải có ý nghĩa về mặt thực tế (sản
    phẩm nổi tiếng có nhiều data phải xếp hạng cao hơn sản phẩm ít
    data).

**Công cụ sử dụng**

- dbt SQL: tính toán Bayesian Score và Controversy Index trong BigQuery.

- BigQuery analytic functions: STDDEV_POP, AVG, COUNT.

**Tài liệu tham khảo**

- Bayesian Average Rating: Wilson Score Interval và ứng dụng trong
  ranking hệ thống (Evan Miller, 2009).

- Microsoft Research — Bayesian inference for ranking:
  https://www.microsoft.com/en-us/research/

- BigQuery analytic functions:
  https://cloud.google.com/bigquery/docs/reference/standard-sql/aggregate_functions

### Tuần 10 — Correlation Attribution Engine

**Các bước thực hiện**

58. Import thư viện ruptures, khởi tạo thuật toán PELT với mô hình RBF
    (Radial Basis Function) để dò tìm change points trong chuỗi thời
    gian sentiment.

59. Viết hàm detect_change_points(sentiment_series, penalty=3) trả về
    danh sách ngày xảy ra thay đổi sentiment đột ngột với biên độ \>
    0.25.

60. Với mỗi change point được phát hiện, viết truy vấn BigQuery tìm
    video YouTube viral (lượt xem \> 100,000) xuất hiện trong khung thời
    gian cộng trừ 7 ngày.

61. Tính Attribution Score cho mỗi sự kiện: temporal_proximity × 0.5 +
    direction_alignment × 0.5. Trong đó temporal_proximity là độ gần
    thời gian (1.0 nếu cùng ngày, giảm dần), direction_alignment là 1.0
    nếu hướng sentiment của video khớp với hướng thay đổi.

62. Gửi dữ liệu sự kiện lên Gemini Flash để sinh câu giải thích tự nhiên
    bằng tiếng Việt, sử dụng từ dè dặt 'có thể', 'tương quan', 'được ghi
    nhận'.

63. Lưu kết quả vào bảng causal_events với các trường: product_id,
    change_point_date, event_video_id, attribution_score,
    explanation_text.

**Công cụ sử dụng**

- ruptures 1.1.9: PELT algorithm (Pruned Exact Linear Time) với RBF cost
  model để phát hiện change points.

- BigQuery: truy vấn tìm video viral trong cửa sổ thời gian ±7 ngày.

- Gemini 2.5 Flash API: sinh câu giải thích tự nhiên bằng tiếng Việt.

**Tài liệu tham khảo**

- ruptures Quick Start: https://centre-borelli.github.io/ruptures-docs/

- PELT algorithm paper: Killick et al. 2012 — Optimal Detection of
  Changepoints with a Linear Computational Cost.

- Event Study Methodology: MacKinlay, 1997 — Event Studies in Economics
  and Finance (Journal of Economic Literature).

#  GIAI ĐOẠN 5 — APPLICATION VÀ BÁO CÁO (Tuần 11–12)

Nguyên tắc tuyệt đối: Không thêm tính năng mới sau tuần 10. Chỉ polish
và fix bugs những gì đã có. Vi phạm nguyên tắc này là nguy cơ lớn nhất
dẫn đến nộp trễ.

### Tuần 11 — Web App FastAPI + Next.js với 2 Actor

**Phạm vi use-case**

| **Actor** | **Use-case chính** | **Mô tả** |
|----|----|----|
| Guest/User | Đăng ký | Tạo tài khoản để sử dụng web app. |
| Guest/User | Đăng nhập/Đăng xuất | Xác thực phiên làm việc và kết thúc phiên an toàn. |
| Guest/User | Tìm kiếm và lọc dữ liệu | Tìm sản phẩm, lọc theo danh mục và các điều kiện phân tích được hỗ trợ. |
| Guest/User | Xem các trang phân tích | Xem bảng xếp hạng, chi tiết khía cạnh và timeline attribution. |
| Guest/User | Đề xuất chỉnh sửa thông tin sản phẩm | Gửi phiếu bổ sung specs, mô tả, URL chính thức hoặc ảnh; không ghi trực tiếp dữ liệu chính. |
| Admin | Quản lý từ khóa tìm kiếm | Xem, thêm, sửa, xóa cấu hình `keyword_config`. |
| Admin | Quản lý kênh tìm kiếm | Xem, thêm, sửa, xóa cấu hình `channel_config`. |
| Admin | Quản lý catalog sản phẩm | CRUD `product_config`, alias và template specs theo danh mục. |
| Admin | Xử lý candidate sản phẩm | Duyệt model chưa nhận diện, sửa mapping video và bổ sung alias chuẩn hóa. |
| Admin | Duyệt phiếu chỉnh sửa | Duyệt hoặc từ chối `product_detail_change_requests`; phiếu được duyệt mới merge vào `product_details`. |
| Admin | Theo dõi Airflow pipeline | Xem health, DAG runs, task status và metrics vận hành. |

Admin kế thừa toàn bộ quyền của Guest/User. Phase 5 chỉ xây dựng **một**
Next.js web app; giao diện điều hướng và quyền truy cập thay đổi theo
role trả về từ FastAPI. Trigger ELT backfill sau khi thay đổi cấu hình là
phần mở rộng sau MVP, không phải điều kiện hoàn thành use-case quản trị.

**Các bước thực hiện**

64. Tạo auth layer FastAPI: PostgreSQL qua SQLAlchemy cho bảng
    `app_users`, hash mật khẩu, JWT access token, role `user|admin`;
    viết `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`,
    `GET /auth/me`. Không dùng BigQuery làm transactional user store.

65. Viết Guest/User endpoints: `GET /products/top/{category}`, `GET
    /products/{id}/aspects`, `GET /products/{id}/attribution`, `GET
    /search?q=...&category=...`, `GET /health`, `POST
    /products/{product_id}/details/requests`.

66. Viết Admin endpoints có dependency `require_admin`: CRUD
    `/admin/keywords` và CRUD `/admin/channels`. Validate dữ liệu đầu
    vào trước khi ghi trực tiếp BigQuery `keyword_config` hoặc
    `channel_config`; ưu tiên soft delete bằng `is_active=FALSE`. Bổ sung
    CRUD `/admin/products`, alias, template specs, candidate resolution,
    video mapping và endpoint duyệt phiếu chỉnh sửa.

67. Cấu hình Redis cache TTL 300 giây cho endpoint đọc analytics; xóa
    cache liên quan sau thao tác quản trị. Không cache endpoint auth.

68. Viết một Next.js App Router web app bằng TypeScript có màn đăng ký,
    đăng nhập, đăng xuất và
    các trang Guest/User: tìm kiếm/lọc, top sản phẩm, chi tiết radar 6
    khía cạnh, timeline sentiment và causal events.

69. Bổ sung các trang chỉ dành cho Admin: quản lý từ khóa, kênh tìm
    kiếm, catalog sản phẩm, alias/template specs, candidate resolution
    và phiếu chỉnh sửa. Ẩn menu quản trị với user thường và bắt buộc
    FastAPI kiểm tra role để ngăn gọi API trực tiếp.

70. Thêm trang Admin Pipeline Health. Next.js gọi FastAPI
    `/admin/pipeline/*`; FastAPI proxy Airflow REST API `/health`,
    `/api/v1/dags`, DAG runs, task instances và kết hợp metrics vận hành
    từ BigQuery. Không đưa Airflow credentials xuống frontend.

71. Test end-to-end theo hai role: đăng ký, đăng nhập, đăng xuất, tìm
    kiếm/lọc, xem analytics, gửi phiếu chỉnh sửa; Admin CRUD
    keyword/channel/catalog và duyệt phiếu; user thường gọi endpoint
    Admin phải nhận `403`; endpoint analytics đã cache phản hồi \< 2
    giây; trang Pipeline Health hiển thị đúng trạng thái DAG gần nhất.

**Công cụ sử dụng**

- FastAPI 0.110: REST API framework.

- Redis 7: in-memory cache, TTL 300 giây.

- Next.js App Router + TypeScript: frontend có routing và điều hướng theo
  role.

- Node.js 20.9+ và npm: runtime frontend Next.js.

- Tailwind CSS + shadcn/ui: layout, form CRUD và bảng Admin.

- Recharts hoặc Plotly.js: radar chart và timeline chart.

- passlib/bcrypt hoặc pwdlib: hash mật khẩu.

- python-jose hoặc PyJWT: ký và kiểm tra JWT.

- SQLAlchemy + PostgreSQL: lưu tài khoản web app trong transactional
  auth store độc lập với BigQuery.

- Docker Compose: tùy chọn đóng gói Backend + Redis + Next.js web app
  trong cùng stack sau giai đoạn development local.

**Tài liệu tham khảo**

- FastAPI documentation: https://fastapi.tiangolo.com/

- Next.js App Router: https://nextjs.org/docs/app

- Next.js Installation: https://nextjs.org/docs/app/getting-started/installation

- Redis Python (redis-py): https://redis-py.readthedocs.io/

### Tuần 12 — Đóng gói Báo cáo và Chuẩn bị Bảo vệ

**Các bước thực hiện**

72. Đóng băng code: không commit tính năng mới sau ngày đầu tuần 12. Chỉ
    hotfix lỗi nghiêm trọng.

73. Vẽ và xuất các sơ đồ chất lượng cao: System Architecture tổng thể,
    Data Flow Diagram (DFD), Database Schema ERD, NLP Pipeline
    Flowchart.

74. Hoàn thiện 5 chương báo cáo: đặc biệt chú trọng Chương 4 Đánh giá —
    cần giải thích trung thực tỷ lệ sai sót của PhoBERT, điều kiện
    Confidence-Routing, giới hạn Attribution Engine.

75. Tạo bảng so sánh model performance: PhoBERT trước fine-tune (~65%
    accuracy), PhoBERT sau fine-tune (~81%), Gemini only (~85%), Hybrid
    Confidence-Routing (~83%).

76. Export sample dataset (~500 câu anonymized) lên HuggingFace Dataset
    Hub để đóng góp học thuật.

77. Chuẩn bị slide bảo vệ nhấn mạnh 3 điểm khác biệt: Hybrid NLP với
    Confidence-Routing, Correlation Attribution Engine, Controversy
    Index.

78. Quay video demo end-to-end backup phòng trường hợp mất mạng tại buổi
    bảo vệ.

79. Ẩn toàn bộ API key khỏi code, push GitHub public.

**Công cụ sử dụng**

- draw.io hoặc Lucidchart: vẽ architecture diagram và ERD.

- HuggingFace Hub: publish dataset.

- GitHub: repository public với README đầy đủ.

**Tài liệu tham khảo**

- HuggingFace dataset upload:
  https://huggingface.co/docs/datasets/upload_dataset

- IEEE Access 2020 — Aspect-Based Sentiment Analysis survey (tham khảo
  cho phần Related Work).

#  ƯỚC TÍNH CHI PHÍ

### Giai đoạn 1 — Data Ingestion

| **Hạng mục chi phí** | **Đơn giá** | **Ước tính dùng** | **Thành tiền** |
|----|:--:|:--:|:--:|
| Google Cloud Storage (lưu JSON) | \$0.023/GB/tháng | ~5GB × 3 tháng | ~\$0.35 |
| BigQuery Storage (tracking tables) | \$0.02/GB/tháng | ~1GB × 3 tháng | ~\$0.06 |
| BigQuery Queries (setup + test) | \$5/TB processed | \< 1GB | ~\$0.00 (free tier) |
| BrightData Residential Proxy | \$10–15/GB | 2–4GB traffic | \$20–\$60 |
| youtube-comment-downloader | Free | \- | \$0 |
| yt-dlp | Free | \- | \$0 |
| YouTube Data API v3 | Free (10K units/ngày) | \- | \$0 |
| TỔNG GIAI ĐOẠN 1 |  |  | \$20 – \$60 |

### Giai đoạn 2 — Data Transformation

| **Hạng mục chi phí** | **Đơn giá** | **Ước tính dùng** | **Thành tiền** |
|----|:--:|:--:|:--:|
| BigQuery dbt run queries | \$5/TB processed | ~5GB × 10 lần run | ~\$0.25 |
| GCS reads (External Table) | \$0.01/10K ops | ~1M reads | ~\$0.10 |
| dbt-bigquery (open source) | Free | \- | \$0 |
| TỔNG GIAI ĐOẠN 2 |  |  | \< \$1 |

### Giai đoạn 3 — NLP Hybrid Pipeline

| **Hạng mục chi phí** | **Đơn giá** | **Ước tính dùng** | **Thành tiền** |
|----|:--:|:--:|:--:|
| Gemini Flash — Auto-Annotation (Tuần 6) | Theo quota API hiện hành | ~40 requests | Phụ thuộc quota |
| Google Colab Pro (nếu cần GPU đảm bảo) | \$10/tháng | 1 tháng | \$0–\$10 |
| Gemini Flash — Confidence Routing (Tuần 8+) | Theo quota API hiện hành | Debug hiện tại fallback tổng khoảng 6% | Phụ thuộc quota |
| HuggingFace Hub (download model) | Free | \- | \$0 |
| underthesea (local) | Free | \- | \$0 |
| PyTorch + Transformers (local) | Free | \- | \$0 |
| TỔNG GIAI ĐOẠN 3 |  |  | \$0 – \$12 |

### Giai đoạn 4 — Analytics Engine

| **Hạng mục chi phí** | **Đơn giá** | **Ước tính dùng** | **Thành tiền** |
|----|:--:|:--:|:--:|
| BigQuery Analytics Queries | \$5/TB processed | ~2GB × 20 lần | ~\$0.20 |
| Gemini 2.5 Flash — Attribution explanations | Theo quota API hiện hành | \< 100 requests | Phụ thuộc quota |
| ruptures (local) | Free | \- | \$0 |
| TỔNG GIAI ĐOẠN 4 |  |  | \< \$1 |

### Giai đoạn 5 — Application và Báo cáo

| **Hạng mục chi phí** | **Đơn giá** | **Ước tính dùng** | **Thành tiền** |
|----|:--:|:--:|:--:|
| Redis (chạy local trong Docker) | Free | \- | \$0 |
| FastAPI + Next.js web app (local) | Free | \- | \$0 |
| JWT auth + password hashing (local) | Free | \- | \$0 |
| BigQuery API reads từ web app | \$5/TB | ~1GB | ~\$0.005 |
| HuggingFace dataset upload | Free | \- | \$0 |
| TỔNG GIAI ĐOẠN 5 |  |  | \< \$1 |

### Tổng chi phí toàn dự án

| **Giai đoạn** | **Thấp nhất** | **Cao nhất** | **Ghi chú** |
|----|:--:|:--:|----|
| Phase 1 — Data Ingestion | \$20 | \$60 | *BrightData proxy là khoản lớn nhất* |
| Phase 2 — Data Transformation | \< \$1 | \< \$1 | *Gần như miễn phí* |
| Phase 3 — NLP Pipeline | \$0 | \$12 | *Colab Pro nếu GPU free không ổn định* |
| Phase 4 — Analytics Engine | \< \$1 | \< \$1 | *Gần như miễn phí* |
| Phase 5 — Application | \< \$1 | \< \$1 | *Gần như miễn phí* |
| **TỔNG TOÀN DỰ ÁN** | **~\$22** | **~\$75** | **Nằm trong ngân sách \$35–\$60** |

**Ghi chú quan trọng về chi phí:**

- GCP cấp \$300 credit miễn phí trong 90 ngày đầu cho tài khoản mới —
  toàn bộ chi phí GCP trong thesis đều nằm trong free credit này.

- BrightData là khoản chi phí thực duy nhất đáng kể, dao động \$20–\$60
  tùy lượng comment cần thu thập.

- Nếu dùng Colab Pro (\$10/tháng) thì chỉ cần 1 tháng là đủ cho toàn bộ
  quá trình fine-tune.

- Gemini API free tier (1,500 requests/ngày) đủ hoàn toàn cho thesis
  dataset — không cần nâng cấp lên paid tier.

***Bảo vệ tốt không phụ thuộc vào số lượng tính năng***

*mà vào độ sâu hiểu biết của từng thứ bạn làm.*

Sentiment Intelligence Platform — Đồ án Tốt nghiệp 2026
