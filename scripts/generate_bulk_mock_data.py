import json
import random
import os
import math
from datetime import datetime, timedelta
import uuid

# Thư mục lưu dữ liệu
OUTPUT_DIR = "data/mock_bulk_data"

# Cấu hình danh sách sản phẩm và phân phối cảm xúc
PRODUCTS = {
    "Điện thoại": [
        {"id": "iphone-16-pro-max", "name": "iPhone 16 Pro Max", "sentiment_profile": "high_positive"},
        {"id": "samsung-galaxy-s24-ultra", "name": "Samsung Galaxy S24 Ultra", "sentiment_profile": "high_positive"},
        {"id": "xiaomi-14", "name": "Xiaomi 14", "sentiment_profile": "balanced"},
        {"id": "oppo-find-x7-ultra", "name": "OPPO Find X7 Ultra", "sentiment_profile": "balanced"},
        {"id": "vivo-x100-pro", "name": "vivo X100 Pro", "sentiment_profile": "random"}
    ],
    "Laptop": [
        {"id": "macbook-pro-14-m3", "name": "MacBook Pro 14 M3", "sentiment_profile": "high_positive"},
        {"id": "dell-xps-14-2024", "name": "Dell XPS 14 2024", "sentiment_profile": "high_positive"},
        {"id": "asus-rog-zephyrus-g14-2024", "name": "ASUS ROG Zephyrus G14 2024", "sentiment_profile": "balanced"},
        {"id": "lenovo-legion-5i-2024", "name": "Lenovo Legion 5i 2024", "sentiment_profile": "balanced"},
        {"id": "hp-spectre-x360-14-2024", "name": "HP Spectre x360 14 2024", "sentiment_profile": "random"}
    ],
    "Tai nghe": [
        {"id": "apple-airpods-pro-2", "name": "Apple AirPods Pro 2", "sentiment_profile": "high_positive"},
        {"id": "sony-wh-1000xm5", "name": "Sony WH-1000XM5", "sentiment_profile": "high_positive"},
        {"id": "samsung-galaxy-buds3-pro", "name": "Samsung Galaxy Buds3 Pro", "sentiment_profile": "balanced"},
        {"id": "bose-quietcomfort-ultra-earbuds", "name": "Bose QuietComfort Ultra Earbuds", "sentiment_profile": "balanced"},
        {"id": "sennheiser-momentum-4-wireless", "name": "Sennheiser Momentum 4 Wireless", "sentiment_profile": "random"}
    ]
}

ASPECTS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]

SENTIMENT_DISTRIBUTIONS = {
    "high_positive": {"positive": 0.85, "neutral": 0.10, "negative": 0.05},
    "balanced": {"positive": 0.35, "neutral": 0.30, "negative": 0.35},
    "random": {"positive": 0.50, "neutral": 0.20, "negative": 0.30},
}

COMMENTS_PER_PRODUCT = 2000
DAYS_IN_PAST = 90
NOW = datetime.now()

# Mảng tên tiếng Việt ngẫu nhiên để tạo author_name
FIRST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
MIDDLE_NAMES = ["Văn", "Thị", "Hữu", "Thanh", "Minh", "Thu", "Ngọc", "Hải", "Tuấn", "Đức", "Hoài", "Phương"]
LAST_NAMES = ["Anh", "Bảo", "Cường", "Dũng", "Hoa", "Lan", "Mai", "Tuấn", "Hùng", "Hương", "Trang", "Long", "Nam", "Linh", "Khang", "Huy"]

def generate_random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(MIDDLE_NAMES)} {random.choice(LAST_NAMES)}"

def get_random_sentiment(profile_name):
    dist = SENTIMENT_DISTRIBUTIONS.get(profile_name, SENTIMENT_DISTRIBUTIONS["random"])
    rand = random.random()
    cum = 0
    for s_type, prob in dist.items():
        cum += prob
        if rand <= cum:
            return s_type
    return "positive"

def generate_date_for_video(video_published_date):
    # Thời gian comment sau video (decay distribution)
    # Phần lớn comment trong 1-7 ngày đầu, rải rác sau đó
    days_after = int(random.expovariate(0.2)) # Trung bình khoảng 5 ngày
    days_after = min(days_after, 60) # Tối đa 60 ngày sau video
    comment_date = video_published_date + timedelta(days=days_after, hours=random.randint(0,23), minutes=random.randint(0,59))
    if comment_date > NOW:
        comment_date = NOW - timedelta(hours=random.randint(1, 24))
    return comment_date

def generate_fake_comment_content(aspect, sentiment):
    # Mock text data based on aspect and sentiment
    templates = {
        "Pin": {
            "positive": ["Pin trâu dã man", "Dùng cả ngày không hết pin", "Pin con này cải thiện nhiều lắm", "Sạc nhanh, pin cực kì ổn"],
            "negative": ["Pin hẻo quá", "Dùng nửa ngày đã phải sạc lại", "Pin tụt như tụt quần", "Sạc thì chậm mà pin thì yếu"],
            "neutral": ["Pin đủ dùng 1 ngày", "Pin bình thường không có gì đặc sắc", "Pin cũng ngang các đời trước"]
        },
        "Camera": {
            "positive": ["Chụp ảnh nét căng", "Camera quay video đỉnh thật sự", "Màu ảnh quá đẹp", "Chụp đêm ngon"],
            "negative": ["Camera chụp hơi bệt", "Quay video bị giật", "Màu sắc nhợt nhạt", "Noise nhiều khi chụp thiếu sáng"],
            "neutral": ["Cam ở mức chấp nhận được", "Chụp chống mù", "Camera cũng ổn định"]
        },
        "Màn hình": {
            "positive": ["Màn hình sáng đẹp", "Tần số quét cao vuốt mượt", "Độ phân giải siêu nét", "Hiển thị màu sắc tuyệt vời"],
            "negative": ["Màn hình hơi tối", "Viền màn hình còn dày", "Bị ám xanh", "Cảm ứng đôi lúc không nhạy"],
            "neutral": ["Màn hình đủ sắc nét", "Hiển thị ở mức trung bình", "Không khác màn đời cũ mấy"]
        },
        "Hiệu năng": {
            "positive": ["Chơi game mượt mà", "Máy quá khỏe, không giật lag", "Cân mọi tựa game", "Mở app nhanh thoăn thoắt"],
            "negative": ["Máy nóng nhanh", "Chơi game lâu bị tụt fps", "Thỉnh thoảng đơ máy", "Chip này hơi phế"],
            "neutral": ["Hiệu năng đủ dùng cơ bản", "Máy chạy tác vụ thường ổn định", "Cũng mượt nhưng chưa thật sự nổi bật"]
        },
        "Thiết kế": {
            "positive": ["Thiết kế sang trọng", "Cầm nắm ôm tay", "Màu mới quá đẹp", "Hoàn thiện cực tốt"],
            "negative": ["Thiết kế lặp lại", "Máy hơi nặng", "Viền camera thô quá", "Mặt lưng dễ bám vân tay"],
            "neutral": ["Thiết kế không có gì đột phá", "Trông cũng bình thường", "Cầm tạm ổn"]
        },
        "Giá": {
            "positive": ["Giá quá hời", "Giá này thì vô địch", "P/p quá tốt", "Đáng từng đồng"],
            "negative": ["Ngáo giá", "Giá này mua hãng khác ngon hơn", "Quá đắt so với cấu hình", "Chờ giảm giá mới mua nổi"],
            "neutral": ["Giá hợp lý", "Mức giá chung của phân khúc", "Giá này cũng có thể chấp nhận"]
        }
    }
    options = templates.get(aspect, {}).get(sentiment, ["..."])
    return random.choice(options) + " " + "".join(random.choices(["!", " :D", " =))", " nha", " quá", " ạ"], k=random.randint(0, 1)))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_mentions = []
    
    # Generate data
    for category, product_list in PRODUCTS.items():
        for product in product_list:
            print(f"Generating data for {product['name']}...")
            
            # Mỗi sản phẩm giả lập 5-10 video chứa comment để timeline có độ chụm (spikes) thay vì rải đều
            num_videos = random.randint(5, 10)
            videos = []
            for _ in range(num_videos):
                # Video đăng ngẫu nhiên trong 90 ngày qua
                video_date = NOW - timedelta(days=random.randint(10, DAYS_IN_PAST))
                videos.append({
                    "video_id": f"vid_{uuid.uuid4().hex[:8]}",
                    "published_at": video_date
                })
            
            for _ in range(COMMENTS_PER_PRODUCT):
                video = random.choice(videos)
                published_at = generate_date_for_video(video["published_at"])
                mention_date = published_at.strftime("%Y-%m-%d")
                
                aspect = random.choice(ASPECTS)
                sentiment = get_random_sentiment(product["sentiment_profile"])
                content = generate_fake_comment_content(aspect, sentiment)
                
                mention = {
                    "mention_id": f"mnt_{uuid.uuid4().hex[:12]}",
                    "video_id": video["video_id"],
                    "comment_id": f"cmt_{uuid.uuid4().hex[:12]}",
                    "sentence_id": f"sent_{uuid.uuid4().hex[:12]}",
                    "author_name": generate_random_name(),
                    "published_at": published_at.isoformat(),
                    "mention_date": mention_date,
                    "content": content,
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "category": category,
                    "aspect": aspect,
                    "sentiment": sentiment,
                    "confidence_score": round(random.uniform(0.75, 0.99), 4),
                    "is_from_fallback": random.random() < 0.05 # 5% từ fallback LLM
                }
                all_mentions.append(mention)

    # Sort theo thời gian
    all_mentions.sort(key=lambda x: x["published_at"])
    
    # Xuất file json lớn
    output_file = os.path.join(OUTPUT_DIR, "fact_product_mentions_mock.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_mentions, f, ensure_ascii=False, indent=2)
    
    # Có thể tách ra định dạng NDJSON (New-line Delimited JSON) giống chuẩn BigQuery
    ndjson_file = os.path.join(OUTPUT_DIR, "fact_product_mentions_mock.ndjson")
    with open(ndjson_file, "w", encoding="utf-8") as f:
        for m in all_mentions:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            
    print(f"\nDone! Generated {len(all_mentions)} mentions.")
    print(f"Files saved to: {OUTPUT_DIR}")
    print(f"- {output_file}")
    print(f"- {ndjson_file}")

if __name__ == "__main__":
    main()
