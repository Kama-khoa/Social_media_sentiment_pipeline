import os
import json
import uuid
import random
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud import storage
import math

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DATASET = os.environ.get("BQ_DATASET")
GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME")

def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)

def get_gcs_client() -> storage.Client:
    return storage.Client(project=PROJECT_ID)

def delete_old_mock_data(bq: bigquery.Client):
    print("Deleting old mock data...")
    tables = [
        "product_config",
        "product_details",
        "video_crawl_state",
        "raw_sentiment_results"
    ]
    for table in tables:
        if table in ["video_crawl_state", "raw_sentiment_results"]:
            query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.{table}` WHERE keyword_id LIKE 'mock_%'"
            if table == "raw_sentiment_results":
                # We can't delete directly by keyword_id if it's not there, wait, raw_sentiment_results has result_id starting with 'mock_'?
                query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.{table}` WHERE result_id LIKE 'mock_%'"
        else:
            query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.{table}` WHERE product_id LIKE 'mock_%'"
        try:
            bq.query(query).result()
            print(f"Deleted old mock data from {table}")
        except Exception as e:
            print(f"Error deleting from {table}: {e}")
            
    # delete from api comments
    try:
        query = f"DELETE FROM `{PROJECT_ID}.{DATASET}.raw_comments_api` WHERE comment_id LIKE 'mock_%'"
        bq.query(query).result()
        print("Deleted old mock data from raw_comments_api")
    except Exception as e:
        print(f"Error deleting from raw_comments_api: {e}")

CATEGORIES = [
    ("Điện thoại", ["Apple", "Samsung", "Xiaomi", "Oppo", "Vivo"]),
    ("Laptop", ["Dell", "HP", "Asus", "Acer", "Lenovo", "MacBook"]),
    ("Tai nghe", ["Sony", "AirPods", "Jabra", "Bose", "Sennheiser"])
]

PHONE_SPECS = {
    "màn_hình": ["6.1 inch OLED", "6.7 inch Super AMOLED", "6.5 inch IPS LCD", "6.8 inch Dynamic AMOLED"],
    "chipset": ["Snapdragon 8 Gen 2", "A17 Pro", "Dimensity 9200+", "Snapdragon 7+ Gen 2"],
    "ram": ["8GB", "12GB", "16GB"],
    "rom": ["128GB", "256GB", "512GB", "1TB"],
    "pin": ["4000 mAh", "4500 mAh", "5000 mAh", "5500 mAh"]
}

LAPTOP_SPECS = {
    "màn_hình": ["13.3 inch FHD", "14 inch 2.8K OLED", "15.6 inch FHD 144Hz", "16 inch QHD+ 165Hz"],
    "cpu": ["Core i5-1340P", "Core i7-13700H", "Ryzen 7 7840HS", "Apple M3 Pro"],
    "ram": ["16GB DDR5", "32GB LPDDR5x", "8GB DDR4"],
    "gpu": ["RTX 4050 6GB", "RTX 4060 8GB", "Intel Iris Xe", "Radeon 780M"],
    "ổ_cứng": ["512GB NVMe", "1TB Gen4 SSD", "2TB NVMe"]
}

HEADPHONE_SPECS = {
    "loại": ["In-ear", "Over-ear", "True Wireless", "Neckband"],
    "chống_ồn": ["Có ANC", "Không ANC", "Cảnh báo tiếng ồn"],
    "thời_lượng_pin": ["5 giờ", "8 giờ", "24 giờ (kèm hộp)", "40 giờ"],
    "bluetooth": ["5.0", "5.2", "5.3", "LDAC support"]
}

ASPECTS = {
    "Điện thoại": ["camera", "pin", "màn hình", "hiệu năng", "thiết kế", "giá"],
    "Laptop": ["màn hình", "bàn phím", "tản nhiệt", "hiệu năng", "pin", "thiết kế"],
    "Tai nghe": ["âm thanh", "chống ồn", "pin", "cảm giác đeo", "mic", "kết nối"]
}

REALISTIC_REVIEWS = {
    "Điện thoại": {
        "POSITIVE": [
            "Máy dùng quá mượt, pin trâu cực kỳ, đáng tiền lắm",
            "Màn hình sáng đẹp, chơi game Genshin không bị nóng",
            "Camera chụp đêm sáng rõ, zoom xa vẫn nét, rất ưng ý",
            "Thiết kế viền mỏng đẹp mê ly, cầm cực kỳ đầm tay",
            "Giá này mua con này là p/p vô địch rồi không phải nghĩ"
        ],
        "NEGATIVE": [
            "Pin hẻo quá, xài mới nửa ngày đã phải cắm sạc",
            "Chụp ảnh bị bệt màu, không nét như quảng cáo",
            "Máy nóng như cái lò khi chơi game nặng, tụt fps liên tục",
            "Phần mềm nhiều lỗi vặt, thi thoảng bị đơ vuốt không ăn",
            "Viền dày cộp, thiết kế nhìn phèn quá, không xứng đáng giá tiền"
        ],
        "NEUTRAL": [
            "Dùng tạm ổn trong tầm giá, không có gì nổi bật",
            "Pin đủ dùng 1 ngày, camera chụp đủ sáng thì đẹp",
            "Máy hơi nóng nhưng bù lại sạc nhanh 120W cũng tiện",
            "Cấu hình mức khá, màn hình tần số quét 60Hz hơi tiếc",
            "Chất lượng build nhựa nhưng được cái nhẹ nhàng"
        ]
    },
    "Laptop": {
        "POSITIVE": [
            "Bàn phím gõ sướng tay, touchpad nhạy mượt như Mac",
            "Render video 4K ầm ầm, tản nhiệt mát rượi, rất tuyệt",
            "Màn OLED màu sắc quá rực rỡ, xem phim bao phê",
            "Build kim loại nguyên khối xịn sò, mỏng nhẹ tiện mang đi làm",
            "Pin trụ được cả ngày làm việc văn phòng, không cần đem sạc"
        ],
        "NEGATIVE": [
            "Tản nhiệt ồn như máy cày, render xíu là rít lên",
            "Bản lề ọp ẹp quá, gõ phím mà màn hình cứ rung rinh",
            "Màn hình sai màu nhiều, không làm đồ hoạ được",
            "Pin tuột như uống nước, rút sạc ra là giảm hiệu năng rõ rệt",
            "Phím hành trình nông, gõ lâu rất mỏi tay"
        ],
        "NEUTRAL": [
            "Cấu hình đủ dùng cho sinh viên học IT",
            "Máy mỏng nhẹ nhưng phải đánh đổi lấy nhiệt độ",
            "Màn hình chống chói tốt nhưng độ sáng hơi thấp",
            "Giá hơi cao nhưng build quality cũng tạm chấp nhận được",
            "Bàn phím không có numpad hơi bất tiện khi nhập số liệu"
        ]
    },
    "Tai nghe": {
        "POSITIVE": [
            "Bass đập cực căng, chống ồn cách ly hoàn toàn với bên ngoài",
            "Pin trâu thật sự, xài cả tuần chưa thấy báo hết",
            "Đeo êm tai vô cùng, nghe nhạc liên tục 3 tiếng không bị đau",
            "Kết nối app điện thoại mượt mà, nhiều tuỳ chỉnh EQ hay ho",
            "Mic đàm thoại rõ ràng, đi xe máy mà bên kia vẫn nghe rõ"
        ],
        "NEGATIVE": [
            "Chống ồn như không, vẫn nghe rõ tiếng xe cộ ồn ào",
            "Bị rớt kết nối liên tục, đang nghe tự nhiên tịt một bên",
            "Đeo bí bách quá, được 1 lúc là đau vành tai",
            "Chất âm lùng bùng, treble bị chói gắt rất khó chịu",
            "Mic thu âm kém, gọi điện toàn bị chê là nói không nghe tiếng"
        ],
        "NEUTRAL": [
            "Âm thanh cân bằng, nghe tạp tốt, không có gì xuất sắc",
            "Đeo vừa vặn, thi thoảng vận động mạnh mới bị rớt",
            "Chống ồn mức khá, lọc được tiếng quạt nhưng tiếng người thì thua",
            "Hộp sạc thiết kế hơi to, bỏ túi quần bị cộm",
            "Chất âm tàm tạm trong tầm giá, mua chữa cháy thì ổn"
        ]
    }
}

def generate_specs(cat_name, index):
    specs = {}
    if cat_name == "Điện thoại":
        specs["màn_hình"] = random.choice(PHONE_SPECS["màn_hình"])
        specs["chipset"] = random.choice(PHONE_SPECS["chipset"])
        specs["ram"] = random.choice(PHONE_SPECS["ram"])
        specs["rom"] = random.choice(PHONE_SPECS["rom"])
        specs["pin"] = random.choice(PHONE_SPECS["pin"])
    elif cat_name == "Laptop":
        specs["màn_hình"] = random.choice(LAPTOP_SPECS["màn_hình"])
        specs["cpu"] = random.choice(LAPTOP_SPECS["cpu"])
        specs["ram"] = random.choice(LAPTOP_SPECS["ram"])
        specs["gpu"] = random.choice(LAPTOP_SPECS["gpu"])
        specs["ổ_cứng"] = random.choice(LAPTOP_SPECS["ổ_cứng"])
    else:
        specs["loại"] = random.choice(HEADPHONE_SPECS["loại"])
        specs["chống_ồn"] = random.choice(HEADPHONE_SPECS["chống_ồn"])
        specs["thời_lượng_pin"] = random.choice(HEADPHONE_SPECS["thời_lượng_pin"])
        specs["bluetooth"] = random.choice(HEADPHONE_SPECS["bluetooth"])
    return specs

def get_review_text(category, sentiment):
    return random.choice(REALISTIC_REVIEWS[category][sentiment])

def upload_ndjson_to_gcs(gcs_client: storage.Client, bucket_name: str, blob_path: str, records: list):
    bucket = gcs_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    ndjson = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    blob.upload_from_string(ndjson.encode("utf-8"), content_type="application/x-ndjson")

def generate_mock_data():
    bq_client = get_bq_client()
    gcs_client = get_gcs_client()
    
    delete_old_mock_data(bq_client)

    now = datetime.now()
    start_date = now - timedelta(days=30)
    mock_partition_date = now.strftime("%Y-%m-%d")

    product_configs = []
    product_details = []
    crawl_states_bq = []
    sentiment_results_bq = []
    videos_gcs = []
    comments_api_bq = []

    product_count = 100
    
    print("Generating mock data...")

    for cat_name, brands in CATEGORIES:
        for i in range(product_count):
            brand = random.choice(brands)
            product_id = f"mock_{cat_name.lower().replace(' ', '_')}_{i+1}"
            product_name = f"Mock {brand} {cat_name} {i+1} Pro"
            
            product_configs.append({
                "product_id": product_id,
                "category": cat_name,
                "product_name": product_name,
                "brand": brand,
                "release_year": random.choice([2023, 2024, 2025]),
                "is_active": True,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            })

            product_details.append({
                "product_id": product_id,
                "specs": json.dumps(generate_specs(cat_name, i), ensure_ascii=False),
                "description": f"Sản phẩm {cat_name} cực kỳ đáng chú ý từ {brand} với nhiều tính năng cao cấp.",
                "official_url": f"https://www.{brand.lower()}.com/{cat_name.lower()}/{i+1}",
                "image_url": f"https://mock-images.com/{cat_name.lower()}_{i+1}.png",
                "updated_at": now.isoformat(),
                "updated_by": "mock_generator"
            })

            change_point_offset = random.randint(10, 20)
            change_date = start_date + timedelta(days=change_point_offset)
            
            initial_sentiment = random.choice(["POSITIVE", "NEGATIVE"])
            new_sentiment = "NEGATIVE" if initial_sentiment == "POSITIVE" else "POSITIVE"
            
            # Viral video
            viral_video_id = f"v_{uuid.uuid4().hex[:10]}"
            videos_gcs.append({
                "video_id": viral_video_id,
                "channel_id": "UC_mock_channel_viral",
                "title": f"Sự thật chấn động về {product_name} - Review {'tích cực' if new_sentiment == 'POSITIVE' else 'tiêu cực'} chưa từng thấy!",
                "description": "Mock viral video for PELT trigger",
                "view_count": random.randint(150_000, 2_000_000),
                "like_count": random.randint(10000, 50000),
                "comment_count": 5000,
                "duration_seconds": 600,
                "tags": [cat_name, brand, "review"],
                "thumbnail_url": "",
                "published_at": change_date.isoformat(),
                "search_mode": "daily",
                "keyword_matched": product_id,
                "gcs_partition_date": mock_partition_date,
                "crawled_at": now.isoformat()
            })

            crawl_states_bq.append({
                "video_id": viral_video_id,
                "channel_id": "UC_mock_channel_viral",
                "keyword_id": product_id,
                "search_mode": "daily",
                "published_at": change_date.isoformat(),
                "maturity_stage": "mature",
                "comment_count": 5000,
                "last_comment_crawled_at": now.isoformat(),
                "created_at": change_date.isoformat(),
                "updated_at": now.isoformat()
            })

            for day_offset in range(30):
                current_date = start_date + timedelta(days=day_offset)
                
                # After change date, we drastically increase mention count and amplitude
                if current_date >= change_date:
                    daily_sentiment = new_sentiment
                    mentions_today = random.randint(30, 50) 
                    target_video_id = viral_video_id
                else:
                    daily_sentiment = initial_sentiment
                    mentions_today = random.randint(5, 15)
                    
                    target_video_id = f"v_{uuid.uuid4().hex[:10]}"
                    videos_gcs.append({
                        "video_id": target_video_id,
                        "channel_id": "UC_mock_channel_normal",
                        "title": f"Review {product_name} ngày thứ {day_offset}",
                        "description": "Mock normal video",
                        "view_count": random.randint(1000, 50000),
                        "like_count": random.randint(100, 2000),
                        "comment_count": 100,
                        "duration_seconds": 600,
                        "tags": [cat_name, brand],
                        "thumbnail_url": "",
                        "published_at": current_date.isoformat(),
                        "search_mode": "daily",
                        "keyword_matched": product_id,
                        "gcs_partition_date": mock_partition_date,
                        "crawled_at": now.isoformat()
                    })
                    crawl_states_bq.append({
                        "video_id": target_video_id,
                        "channel_id": "UC_mock_channel_normal",
                        "keyword_id": product_id,
                        "search_mode": "daily",
                        "published_at": current_date.isoformat(),
                        "maturity_stage": "mature",
                        "comment_count": 100,
                        "last_comment_crawled_at": now.isoformat(),
                        "created_at": current_date.isoformat(),
                        "updated_at": now.isoformat()
                    })

                for m in range(mentions_today):
                    comment_id = f"mock_c_{uuid.uuid4().hex[:12]}"
                    sentence_id = f"{comment_id}_0"
                    is_main_sentiment = random.random() < 0.85
                    actual_sentiment = daily_sentiment if is_main_sentiment else random.choice(["POSITIVE", "NEGATIVE", "NEUTRAL"])
                    
                    comment_text = get_review_text(cat_name, actual_sentiment)
                    aspect = random.choice(ASPECTS[cat_name])
                    
                    comments_api_bq.append({
                        "comment_id": comment_id,
                        "video_id": target_video_id,
                        "channel_id": "UC_mock",
                        "parent_comment_id": None,
                        "author_channel_id": "UC_author",
                        "author_display_name": "Người dùng Mạng xã hội",
                        "text_original": comment_text,
                        "text_display": comment_text,
                        "like_count": random.randint(0, 100),
                        "reply_count": 0,
                        "is_reply": False,
                        "crawl_type": "api",
                        "published_at": current_date.isoformat(),
                        "updated_at": current_date.isoformat(),
                        "crawled_at": now.isoformat(),
                        "gcs_partition_date": mock_partition_date,
                    })

                    sentiment_results_bq.append({
                        "result_id": f"mock_r_{uuid.uuid4().hex[:12]}",
                        "sentence_id": sentence_id,
                        "aspect_label": aspect,
                        "sentiment_label": actual_sentiment,
                        "confidence_score": round(random.uniform(0.8, 0.99), 4),
                        "created_at": now.isoformat(),
                        "keyword_id": product_id
                    })

    print(f"Uploading {len(videos_gcs)} videos to GCS...")
    upload_ndjson_to_gcs(gcs_client, GCS_BUCKET, f"raw/youtube/{mock_partition_date}/videos/mock_videos.json", videos_gcs)
    
    print("Registering GCS partitions in BigQuery...")
    alter_videos_sql = f"""
    ALTER TABLE `{PROJECT_ID}.{DATASET}.raw_videos`
    ADD IF NOT EXISTS PARTITION (gcs_partition_date = '{mock_partition_date}')
    OPTIONS (uris=['gs://{GCS_BUCKET}/raw/youtube/{mock_partition_date}/videos/*']);
    """
    try:
        bq_client.query(alter_videos_sql).result()
        print("Partition for raw_videos added successfully.")
    except Exception as e:
        print(f"Error adding partition: {e}")

    print("Inserting into BQ native tables (Config, Details, Crawl States, Sentiment)...")
    bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET}.product_config", product_configs)
    bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET}.product_details", product_details)
    
    chunk_size = 5000
    for i in range(0, len(crawl_states_bq), chunk_size):
        bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET}.video_crawl_state", crawl_states_bq[i:i+chunk_size])

    print(f"Inserting {len(comments_api_bq)} comments to raw_comments_api...")
    for i in range(0, len(comments_api_bq), chunk_size):
        bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET}.raw_comments_api", comments_api_bq[i:i+chunk_size])

    print(f"Inserting {len(sentiment_results_bq)} sentiment results into BigQuery...")
    for i in range(0, len(sentiment_results_bq), chunk_size):
        bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET}.raw_sentiment_results", sentiment_results_bq[i:i+chunk_size])
        print(f"Inserted {min(i+chunk_size, len(sentiment_results_bq))}/{len(sentiment_results_bq)}...")

    print("DONE! You can now run dbt to transform the mock data.")

if __name__ == "__main__":
    generate_mock_data()
