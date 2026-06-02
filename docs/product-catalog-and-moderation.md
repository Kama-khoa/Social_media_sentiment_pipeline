# Product Catalog, Resolution và Moderation

## Mục tiêu

Tách từ khóa crawl khỏi sản phẩm chuẩn:

```text
seed_keywords.csv -> keyword_config -> tìm video liên quan
seed_products.csv -> product_config + product_aliases -> nhận diện model chuẩn
```

`dim_products` không còn được tạo từ `keyword_config`. Model dbt đọc
`product_config`, sau đó API ranking join theo `product_id` chuẩn để hiển thị
tên đầy đủ như `Samsung Galaxy S25 Ultra`.

## Bảng dữ liệu mới

### Layer 0 Config

| Bảng | Vai trò |
|---|---|
| `product_config` | Catalog chuẩn: một dòng cho mỗi model sản phẩm |
| `product_aliases` | Tên chính thức, viết tắt và cách gọi phổ biến dùng cho resolver |
| `product_details` | Hồ sơ mô tả và `specs` JSON nullable của sản phẩm |
| `product_spec_templates` | Danh sách key specs hợp lệ theo category, gồm nhãn, kiểu dữ liệu và đơn vị |
| `product_detail_change_requests` | Phiếu đề xuất chỉnh sửa thông tin sản phẩm từ user, chờ admin duyệt |
| `product_resolution_candidates` | Audit và hàng chờ các mention sản phẩm chưa resolve hoặc mơ hồ |
| `video_product_overrides` | Mapping video -> sản phẩm do admin hoặc LLM xác nhận |
| `sentence_product_target_overrides` | Mapping sentence -> sản phẩm và sentiment target-specific cho câu so sánh |

### Layer 3 Intermediate

| Bảng | Vai trò |
|---|---|
| `int_video_product_mentions` | Match alias trong title/description; video đơn model có role `primary` |
| `int_sentence_product_targets` | Target sản phẩm theo sentence: explicit, kế thừa primary hoặc override |
| `int_product_resolution_candidates` | Candidate tự động cho video chưa map và sentence nhiều target |

### Layer 4 Marts

| Bảng | Thay đổi |
|---|---|
| `dim_products` | Đọc từ `product_config`, không đọc từ `keyword_config` |
| `fact_product_mentions` | Có thêm `target_source`, `target_confidence`; dùng target đã resolve |
| `agg_daily_product_ranking` | Tổng hợp sentiment theo `product_id` chuẩn |

## Seed catalog

File `elt/seed_data/seed_products.csv` là nguồn khởi tạo độc lập:

```csv
product_id,product_name,brand,category,release_year,aliases
iphone-17-pro-max,iPhone 17 Pro Max,Apple,Điện thoại,2025,iphone 17 pro max
```

`aliases` dùng dấu `|` để phân tách nhiều cách gọi. Bộ mẫu hiện có 500 dòng:

| Category | Số sản phẩm |
|---|---:|
| Điện thoại | 250 |
| Laptop | 150 |
| Tai nghe | 100 |

Đây là dữ liệu development/demo. Admin cần rà lại model, năm phát hành và alias
trước khi dùng production.

## Luồng resolve sentiment target

```text
raw_videos.title + description
    -> alias resolver
    -> int_video_product_mentions

int_comment_sentences
    -> alias resolver theo sentence
    -> explicit target nếu câu nêu model
    -> inherited_video_primary nếu comment ngầm và video chỉ có một primary
    -> needs_llm nếu câu nhắc nhiều model

needs_llm / video chưa map
    -> nlp.product_target_resolver
    -> override tables
    -> rebuild fact_product_mentions
```

Quy tắc:

- Video đơn sản phẩm: comment như `pin tốt` kế thừa sản phẩm chính.
- Video so sánh: comment không nêu model không tham gia KPI.
- Câu như `S25 pin tốt hơn nhưng camera iPhone đẹp hơn`: resolver LLM tạo
  target-specific sentiment cho từng sản phẩm.
- Resolver LLM chỉ được chọn `product_id` đã tồn tại trong catalog.

## Use case quản lý sản phẩm

| Actor | Use case | Kết quả |
|---|---|---|
| Admin | Tạo hoặc sửa sản phẩm chuẩn | Cập nhật `product_config`; rebuild dbt để cập nhật `dim_products` |
| Admin | Vô hiệu hóa sản phẩm | Soft delete bằng `is_active=FALSE` |
| Admin | Thêm hoặc vô hiệu hóa alias | Resolver nhận diện thêm hoặc bỏ cách gọi của model |
| Admin | Quản lý template specs | Quy định key JSON hợp lệ theo danh mục |
| Admin | Xem mapping video | Kiểm tra sản phẩm được nhận diện từ title/description |
| Admin | Override mapping video | Ghi `video_product_overrides`, được ưu tiên ở lần dbt rebuild tiếp theo |
| Admin | Resolve candidate | Gắn candidate vào product chuẩn; sentence candidate bắt buộc có sentiment |

## Use case phiếu chỉnh sửa thông tin

```text
User đăng nhập
    -> mở trang chi tiết sản phẩm
    -> gửi JSON specs hoặc metadata đề xuất
    -> validate theo product_spec_templates
    -> product_detail_change_requests.status = pending

Admin
    -> xem danh sách phiếu pending
    -> approve hoặc reject
    -> approve: merge field được gửi vào product_details
    -> giữ nguyên field cũ không xuất hiện trong phiếu
```

User không được ghi trực tiếp vào `product_details`. Cơ chế moderation bảo vệ
catalog khỏi dữ liệu sai, spam và thay đổi không có audit.

## Migration và rebuild

```powershell
conda activate etl-py313
python schema/migrate_product_catalog.py

cd transform
dbt run --profiles-dir . --full-refresh
dbt test --profiles-dir .

cd ..
python -m nlp.product_target_resolver --limit 100

cd transform
dbt run --profiles-dir . --select int_video_product_mentions int_sentence_product_targets fact_product_mentions agg_daily_product_ranking
```
