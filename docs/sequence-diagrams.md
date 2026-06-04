# Sequence Diagram Các Chức Năng Chính

Tài liệu này mô tả các luồng tuần tự quan trọng của `Social Media Sentiment Pipeline`.
Các sơ đồ dùng Mermaid `sequenceDiagram`, theme trắng đen, và các nhánh xử lý được đặt trong khung `alt` theo điều kiện nghiệp vụ.

## 1. Khởi Tạo Schema Và Seed Cấu Hình

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000"}}}%%
sequenceDiagram
    autonumber
    actor Operator as Người vận hành
    participant Main as elt.main
    participant Seed as seed_loader
    participant Quota as QuotaBudget
    participant Video as VideoExtractor
    participant Comment as CommentExtractor
    participant GCS as Google Cloud Storage
    participant BQ as BigQuery

    Operator->>Main: python -m elt.main --mode full
    Main->>Seed: sync_channels, sync_keywords, sync_products
    Seed->>BQ: Upsert cấu hình crawl và catalog
    Main->>Quota: Tạo ngân sách quota từ quota_operation_log
    Main->>Video: run_daily(execution_date, dag_run_id, budget)
    Video->>BQ: Đọc active channels và keywords
    Video->>Quota: Kiểm tra quota SEARCH
    Video->>Video: YouTube API search.list theo channel
    Video->>Video: Lọc keyword, dedupe video_id
    Video->>Video: yt-dlp enrich metadata
    Video->>GCS: Upload raw/videos/*.ndjson
    Video->>BQ: Upsert video_crawl_state
    Video->>Comment: crawl_batch_with_retry(video mới)
    Comment->>GCS: Upload raw/comments/*.ndjson
    Comment->>BQ: Cập nhật trạng thái crawl comment
    Main->>Video: run_historical(...)
    Video->>BQ: Lấy channel chưa historical scan
    Video->>Video: yt-dlp flat scan và enrich theo batch
    Video->>GCS: Upload video raw
    Video->>BQ: Upsert crawl state, mark channel scanned
    Video->>Comment: Crawl comment cho batch video
    Main->>Comment: run_backlog(dag_run_id)
    Comment->>BQ: Lấy videos_to_crawl
    Comment->>GCS: Upload comment backlog
    Comment->>BQ: Log quota_operation và quota_daily_summary
    Main-->>Operator: Trả kết quả daily, historical, backlog
```

## 2. ELT Full Pipeline

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant CLI as Command Line
    participant ELT as ELT Backend
    participant Quota as Quota Budget
    participant YT as YouTube API
    participant YTDLP as yt-dlp
    participant GCS as Google Cloud Storage
    participant DB as BigQuery Database

    Operator->>CLI: python -m elt.main --mode full
    CLI->>ELT: Start pipeline
    ELT->>DB: Đồng bộ seed config và catalog
    ELT->>DB: Đọc quota_operation_log hôm nay
    DB-->>ELT: Quota đã dùng theo bucket
    ELT->>Quota: Tạo ngân sách quota cho run hiện tại

    ELT->>DB: Lấy danh sách channel và keyword active
    loop Mỗi channel trong daily scan
        ELT->>Quota: Kiểm tra quota SEARCH
        alt [Còn quota YouTube API]
            ELT->>YT: search.list video mới theo channel
            YT-->>ELT: Danh sách video raw
        else [Hết quota YouTube API]
            ELT-->>CLI: Dừng daily scan, giữ phần historical/backlog
        end
    end

    ELT->>YTDLP: Lọc keyword và enrich metadata
    YTDLP-->>ELT: Video metadata đầy đủ
    ELT->>DB: Kiểm tra video_crawl_state để dedupe
    DB-->>ELT: Video đã crawl

    alt [Có video mới]
        ELT->>GCS: Upload raw/videos/*.ndjson
        ELT->>DB: Upsert video_crawl_state
        ELT->>YTDLP: Crawl comments cho video mới
        YTDLP-->>ELT: Comments raw
        ELT->>GCS: Upload raw/comments/*.ndjson
        ELT->>DB: Cập nhật trạng thái comment crawl
    else [Không có video mới]
        ELT-->>CLI: Bỏ qua upload daily video
    end

    ELT->>DB: Lấy channel chưa historical scan
    alt [Còn channel chưa quét lịch sử]
        ELT->>YTDLP: Historical flat scan và enrich theo batch
        YTDLP-->>ELT: Video lịch sử phù hợp keyword
        ELT->>GCS: Upload raw video lịch sử
        ELT->>DB: Upsert crawl_state và mark channel scanned
    else [Tất cả channel đã historical scan]
        ELT-->>CLI: Bỏ qua historical scan
    end

    ELT->>DB: Lấy videos_to_crawl cho comment backlog
    alt [Có video backlog đủ điều kiện]
        ELT->>YTDLP: Crawl comment backlog
        YTDLP-->>ELT: Comments raw
        ELT->>GCS: Upload raw/comments/*.ndjson
        ELT->>DB: Cập nhật trạng thái crawl
    else [Không có backlog]
        ELT-->>CLI: Bỏ qua comment backlog
    end

    ELT->>DB: Ghi quota_operation và quota_daily_summary
    ELT-->>Operator: Trả kết quả daily, historical, backlog
```

## 3. Daily Scan Video

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant BE as VideoExtractor
    participant DB as BigQuery Database
    participant Quota as Quota Budget
    participant YT as YouTube API
    participant YTDLP as yt-dlp Fetcher
    participant GCS as Google Cloud Storage

    Operator->>BE: run_daily(execution_date, dag_run_id)
    BE->>DB: get_active_channels()
    DB-->>BE: Danh sách channel active
    BE->>DB: get_active_keywords()
    DB-->>BE: Danh sách keyword active

    loop Mỗi channel
        BE->>Quota: can_consume(SEARCH, 100)
        alt [Còn quota]
            BE->>YT: search_channel_recent(channel_id)
            YT-->>BE: Raw video entries
            BE->>Quota: consume(SEARCH, 100)
        else [Không còn quota]
            BE-->>Operator: Dừng quét daily để tránh vượt quota
        end
    end

    BE->>YTDLP: filter_by_keywords(raw videos)
    YTDLP-->>BE: Video khớp keyword
    BE->>DB: get_all_video_ids()
    DB-->>BE: Video đã tồn tại

    alt [Có video mới sau dedupe]
        BE->>YTDLP: enrich_batch(new_videos)
        YTDLP-->>BE: Metadata đầy đủ
        BE->>GCS: upload_json(raw/videos)
        GCS-->>BE: GCS URI
        BE->>DB: bulk_upsert_from_video_dtos()
        DB-->>BE: OK
        BE-->>Operator: Daily scan lưu video mới thành công
    else [Không có video mới]
        BE-->>Operator: Daily scan không phát hiện video mới
    end

    BE->>DB: log_operation(video_extraction_daily)
```

## 4. API Comment Backfill

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant CLI as Command Line
    participant BE as API Comment Backfill
    participant DB as BigQuery Database
    participant Quota as Quota Budget
    participant YT as YouTube Comment API

    Operator->>CLI: python scripts/run_api_comment_backfill.py
    CLI->>DB: Đọc quota đã dùng hôm nay
    DB-->>CLI: used_by_bucket
    CLI->>Quota: Tạo QuotaBudget
    CLI->>BE: run(max_videos, max_comments, dry_run)
    BE->>Quota: remaining(COMMENT_THREADS)

    alt [Hết quota commentThreads]
        BE-->>Operator: Bỏ qua backfill vì quota đã hết
    else [Còn quota commentThreads]
        BE->>DB: Query candidate videos từ stg_youtube_videos JOIN int_video_product_mentions
        DB-->>BE: Danh sách video candidate

        alt [Dry run]
            BE-->>Operator: Trả số candidate và quota ước tính, không gọi API
        else [Chạy backfill thật]
            loop Mỗi video candidate
                BE->>DB: Đọc api_comment_backfill_state
                DB-->>BE: last_page_token, counters, status
                loop Từng page comments
                    BE->>Quota: can_consume(COMMENT_THREADS, 1)
                    alt [Còn quota cho page]
                        BE->>YT: commentThreads.list(video_id, page_token)
                        YT-->>BE: comments, next_page_token
                        BE->>Quota: consume(COMMENT_THREADS, 1)
                        BE->>DB: MERGE raw_comments_api theo comment_id
                        DB-->>BE: Số comment đã merge
                        BE->>DB: Update api_comment_backfill_state
                    else [Quota page đã hết]
                        BE-->>Operator: Dừng backfill và giữ checkpoint
                    end
                end
            end
            BE->>DB: Log quota_operation bucket youtube_api_comments
            BE->>DB: Upsert quota_daily_summary
            BE-->>Operator: Trả videos_processed, comments_merged, quota_units_used
        end
    end
```

## 5. dbt Transform Raw Sang Marts

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant CLI as dbt Runner
    participant DBT as dbt Core
    participant GCS as Google Cloud Storage
    participant DB as BigQuery Database

    Operator->>CLI: python scripts/dbt/dbt_runner.py run
    CLI->>DBT: dbt run --select models
    DBT->>DB: Đọc raw_videos external table
    DB->>GCS: Đọc raw/videos/*.ndjson
    GCS-->>DB: Raw video data
    DBT->>DB: Đọc raw_comments và raw_comments_api

    DBT->>DB: Build stg_youtube_videos
    DBT->>DB: Build stg_youtube_comments
    DBT->>DB: Build int_video_product_mentions
    DBT->>DB: Build int_comment_sentences

    alt [Đã có raw_sentiment_results]
        DBT->>DB: Build int_sentiment_results
        DBT->>DB: Build int_sentence_product_targets
        DBT->>DB: Build fact_product_mentions
        DBT->>DB: Build agg_daily_product_ranking
        DB-->>DBT: Marts analytics sẵn sàng
    else [Chưa chạy NLP]
        DBT-->>Operator: Chỉ có staging/intermediate, cần chạy NLP trước khi build fact/ranking
    end

    DBT-->>Operator: Hoàn tất dbt run
```

## 6. NLP Hybrid Sentiment Analysis

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant CLI as Command Line
    participant BE as NLP Runner
    participant DB as BigQuery Database
    participant NER as vELECTRA Aspect Model
    participant CLS as PhoBERT Sentiment Model
    participant LLM as Gemini Fallback

    Operator->>CLI: python -m nlp.runner --limit N
    CLI->>BE: Start NLP inference
    BE->>DB: Query int_comment_sentences chưa xử lý
    DB-->>BE: Danh sách sentence hợp lệ

    loop Mỗi sentence
        BE->>NER: Extract aspect và segment
        NER-->>BE: aspect_label, segment_text, ner_confidence

        alt [aspect_label = NONE]
            BE->>DB: Chuẩn bị result NEUTRAL/NONE
        else [NER confidence < threshold]
            BE->>LLM: Đưa sentence vào Gemini fallback queue
            LLM-->>BE: aspect + sentiment annotation
        else [NER confidence đạt threshold]
            BE->>CLS: Classify sentiment theo aspect
            CLS-->>BE: sentiment_label, sentiment_confidence

            alt [Sentiment confidence < threshold]
                BE->>LLM: Đưa sentence vào Gemini fallback queue
                LLM-->>BE: aspect + sentiment annotation
            else [Sentiment confidence đạt threshold]
                BE->>DB: Chuẩn bị result source=model
            end
        end
    end

    alt [Có result rows]
        BE->>DB: Load rows vào staging table tạm
        BE->>DB: MERGE raw_sentiment_results theo result_id
        BE->>DB: Xóa staging table tạm
        DB-->>BE: Commit thành công
        BE-->>Operator: Trả số result rows đã ghi
    else [Không có sentence cần xử lý]
        BE-->>Operator: Không ghi BigQuery, pipeline NLP kết thúc
    end
```

## 7. Resolve Product Target Mơ Hồ

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    actor Admin as Admin
    participant CLI as Command Line
    participant BE as Product Target Resolver
    participant API as Admin Backend
    participant LLM as Gemini
    participant DB as BigQuery Database

    Operator->>CLI: dbt run --select int_product_resolution_candidates
    CLI->>DB: Build candidates từ video/sentence mơ hồ
    DB-->>CLI: Candidate table ready

    Operator->>CLI: python -m nlp.product_target_resolver --limit N
    CLI->>BE: Start auto resolver
    BE->>DB: Đọc product_config và product_aliases
    DB-->>BE: Catalog hợp lệ
    BE->>DB: Đọc pending candidates
    DB-->>BE: Candidate batch
    BE->>LLM: Resolve candidate batch bằng catalog
    LLM-->>BE: product_ids, targets, confidence, reason

    alt [Confidence đủ auto approve]
        BE->>DB: MERGE video_product_overrides nếu source_type=video
        BE->>DB: MERGE sentence_product_target_overrides nếu source_type=sentence
        BE->>DB: Audit product_resolution_candidates status=approved
        alt [Có alias_suggestion hợp lệ]
            BE->>DB: INSERT product_aliases
        else [Không có alias_suggestion]
            BE-->>CLI: Không tạo alias mới
        end
    else [Confidence chưa đủ]
        BE->>LLM: Recheck batch lần hai
        LLM-->>BE: Kết quả audit lại
        alt [Recheck đủ auto approve]
            BE->>DB: Ghi override và audit approved
        else [Vẫn mơ hồ]
            BE->>DB: Audit product_resolution_candidates status=pending
        end
    end

    Admin->>API: POST /admin/products/resolution-candidates/{id}/review
    API->>DB: Lấy candidate computed
    DB-->>API: Candidate detail
    alt [Admin approve video candidate]
        API->>DB: MERGE product_resolution_candidates status=approved
        API->>DB: MERGE video_product_overrides
    else [Admin approve sentence candidate]
        API->>DB: MERGE product_resolution_candidates status=approved
        API->>DB: MERGE sentence_product_target_overrides với sentiment_label
    end
    API-->>Admin: HTTP 200, candidate approved
```

## 8. Analytics PELT Attribution

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Operator as Người vận hành
    participant CLI as Command Line
    participant BE as PELT Attribution
    participant Algo as ruptures.Pelt
    participant LLM as Gemini
    participant DB as BigQuery Database

    Operator->>CLI: python -m analytics.pelt_attribution
    CLI->>BE: Start attribution
    BE->>DB: Query fact_product_mentions JOIN dim_products
    DB-->>BE: Daily avg_sentiment theo product

    loop Mỗi product
        BE->>BE: Kiểm tra min_points, coverage, gap interpolation
        alt [Không đủ dữ liệu time series]
            BE-->>CLI: Skip product
        else [Đủ dữ liệu time series]
            BE->>Algo: Detect change points
            Algo-->>BE: Danh sách change points

            loop Mỗi change point
                BE->>BE: Tính amplitude trước/sau
                alt [Amplitude không đủ ngưỡng]
                    BE-->>CLI: Bỏ qua change point
                else [Amplitude đủ ngưỡng]
                    BE->>DB: Query viral videos quanh change_date
                    DB-->>BE: Video candidates

                    alt [Không có viral video candidate]
                        BE-->>CLI: Skip event
                    else [Có viral video candidate]
                        BE->>DB: Query video sentiment và comment tiêu biểu
                        DB-->>BE: Sentiment score và comments
                        BE->>BE: Chọn video có attribution_score cao nhất

                        alt [Dry run]
                            BE-->>Operator: Log event candidate, không ghi database
                        else [Chạy thật]
                            BE->>LLM: Generate explanation_text
                            LLM-->>BE: Giải thích tương quan
                            BE->>DB: INSERT causal_events nếu event_id chưa tồn tại
                            DB-->>BE: OK
                        end
                    end
                end
            end
        end
    end

    BE-->>Operator: Hoàn tất PELT attribution
```

## 9. Public Dashboard Và Product Detail

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor User as Người dùng
    participant FE as Frontend
    participant BE as Backend
    participant Cache as Redis Cache
    participant DB as BigQuery Database

    User->>FE: Mở trang ranking sản phẩm
    FE->>BE: GET /products/top/{category}
    BE->>Cache: Kiểm tra cache products:top

    alt [Cache HIT]
        Cache-->>BE: Ranking JSON
        BE-->>FE: HTTP 200, X-Cache=HIT
        FE-->>User: Hiển thị ranking sản phẩm
    else [Cache MISS]
        BE->>DB: Query agg_daily_product_ranking JOIN dim_products
        DB-->>BE: Dữ liệu ranking mới nhất
        BE->>Cache: Lưu cache TTL 300 giây
        BE-->>FE: HTTP 200, X-Cache=MISS
        FE-->>User: Hiển thị ranking sản phẩm
    end

    User->>FE: Bấm xem chi tiết sản phẩm X
    FE->>BE: GET /products/{product_id}/aspects
    BE->>Cache: Kiểm tra cache product aspects

    alt [Cache HIT]
        Cache-->>BE: Product detail JSON
        BE-->>FE: HTTP 200
    else [Cache MISS]
        BE->>DB: Query dim_products, product_details, ranking
        BE->>DB: Query fact_product_mentions theo aspect
        BE->>DB: Query product_spec_templates
        DB-->>BE: Product detail data
        BE->>Cache: Lưu cache TTL 300 giây
        BE-->>FE: HTTP 200
    end

    FE-->>User: Render specs, aspect sentiment, điểm ranking
    FE->>BE: GET /products/{product_id}/comments
    BE->>DB: Query comment tiêu biểu từ fact_product_mentions
    DB-->>BE: Danh sách comment
    BE-->>FE: HTTP 200
    FE-->>User: Hiển thị bình luận tiêu biểu
```

## 10. Đăng Nhập Admin Và Vận Hành Pipeline

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor Admin as Admin
    participant FE as Frontend
    participant BE as Backend
    participant LocalDB as SQLite Database
    participant Airflow as Airflow API
    participant DB as BigQuery Database

    Admin->>FE: Nhập email và password
    FE->>BE: POST /auth/login
    BE->>LocalDB: Tìm app_users theo email
    LocalDB-->>BE: User record

    alt [Thông tin đăng nhập hợp lệ]
        BE-->>FE: HTTP 200, JWT access_token
        FE-->>Admin: Đăng nhập thành công
        Admin->>FE: Mở dashboard admin
        FE->>BE: GET /dashboard/admin với Bearer token
        BE->>BE: require_admin()

        alt [Token hợp lệ và role admin]
            BE->>DB: Query quick stats, quota, attention items
            DB-->>BE: Dashboard metrics
            BE->>Airflow: GET /health và DAG runs
            Airflow-->>BE: Scheduler, webserver, DAG status
            BE-->>FE: HTTP 200 AdminDashboardResponse
            FE-->>Admin: Hiển thị dashboard vận hành
        else [Token thiếu quyền admin]
            BE-->>FE: HTTP 403 Forbidden
            FE-->>Admin: Không có quyền truy cập
        end
    else [Sai email hoặc password]
        BE-->>FE: HTTP 401 Unauthorized
        FE-->>Admin: Hiển thị lỗi đăng nhập
    end

    Admin->>FE: Bấm Trigger DAG
    FE->>BE: POST /admin/pipeline/dags/{dag_id}/trigger
    BE->>BE: require_admin()

    alt [Airflow kết nối thành công]
        BE->>Airflow: POST /api/v1/dags/{dag_id}/dagRuns
        Airflow-->>BE: dag_run metadata
        BE-->>FE: HTTP 200
        FE-->>Admin: DAG đã được trigger
    else [Airflow lỗi hoặc timeout]
        BE-->>FE: HTTP 502/504
        FE-->>Admin: Hiển thị lỗi kết nối Airflow
    end
```

## 11. User Đề Xuất Chỉnh Sửa Product Detail Và Admin Duyệt

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#ffffff", "primaryColor": "#ffffff", "primaryBorderColor": "#000000", "primaryTextColor": "#000000", "lineColor": "#000000", "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "actorBorder": "#000000", "actorTextColor": "#000000", "signalColor": "#000000", "signalTextColor": "#000000", "noteBkgColor": "#ffffff", "noteTextColor": "#000000", "noteBorderColor": "#000000", "activationBorderColor": "#000000", "activationBkgColor": "#ffffff"}}}%%
sequenceDiagram
    actor User as User đăng nhập
    actor Admin as Admin
    participant FE as Frontend
    participant BE as Backend
    participant DB as BigQuery Database
    participant Cache as Redis Cache

    User->>FE: Gửi đề xuất specs, description, URL, image
    FE->>BE: POST /products/{product_id}/details/requests
    BE->>BE: get_current_user()
    BE->>DB: Truy vấn product_spec_templates
    DB-->>BE: Template specs hợp lệ
    BE->>BE: validate_specs(product_id, specs)

    alt [Specs hợp lệ]
        BE->>DB: INSERT product_detail_change_requests status=pending
        DB-->>BE: OK
        BE-->>FE: HTTP 201, request_id
        FE-->>User: Đã gửi phiếu chờ duyệt
    else [Specs sai template]
        BE-->>FE: HTTP 422 Validation Error
        FE-->>User: Hiển thị lỗi cấu trúc specs
    end

    Admin->>FE: Vào danh sách phiếu chờ duyệt
    FE->>BE: GET /admin/products/detail-requests?status=pending
    BE->>BE: require_admin()
    BE->>DB: Query product_detail_change_requests pending
    DB-->>BE: Danh sách request
    BE-->>FE: HTTP 200
    FE-->>Admin: Hiển thị danh sách request

    Admin->>FE: Mở request và chọn hành động review
    FE->>BE: POST /admin/products/detail-requests/{request_id}/review
    BE->>BE: require_admin()
    BE->>DB: Lấy request pending
    DB-->>BE: Request detail

    alt [Admin approve]
        BE->>BE: validate_specs theo template
        BE->>DB: MERGE product_details bằng JSON_MERGE_PATCH
        DB-->>BE: Product details updated
        BE->>DB: UPDATE request status=approved
        BE->>Cache: invalidate_prefix(products:)
        BE-->>FE: HTTP 200, status=approved
        FE-->>Admin: Phiếu đã được phê duyệt
    else [Admin reject]
        BE->>DB: UPDATE request status=rejected, review_note
        DB-->>BE: Request rejected
        BE->>Cache: invalidate_prefix(products:)
        BE-->>FE: HTTP 200, status=rejected
        FE-->>Admin: Phiếu đã bị từ chối
    end
```
