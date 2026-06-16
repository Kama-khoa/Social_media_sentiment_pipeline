import os
import uuid
import random
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

print("Fetching mock sentences from int_comment_sentences...")
query = f"""
    SELECT s.sentence_id, s.comment_id, s.video_id, s.sentence_text, c.text_original
    FROM `{project}.{dataset}_intermediate.int_comment_sentences` s
    JOIN `{project}.{dataset}.raw_comments_api` c ON s.comment_id = c.comment_id
    WHERE s.comment_id LIKE 'mock_%'
"""
rows = list(client.query(query).result())
print(f"Found {len(rows)} mock sentences.")

ASPECTS = {
    "Điện thoại": ["camera", "pin", "màn hình", "hiệu năng", "thiết kế", "giá"],
    "Laptop": ["màn hình", "bàn phím", "tản nhiệt", "hiệu năng", "pin", "thiết kế"],
    "Tai nghe": ["âm thanh", "chống ồn", "pin", "cảm giác đeo", "mic", "kết nối"]
}

sentiment_results = []
now = datetime.now().isoformat()

for row in rows:
    text = row.text_original
    
    # Simple heuristic to find category and sentiment from the text
    category = "Điện thoại"
    if "Bàn phím" in text or "tản nhiệt" in text or "bản lề" in text:
        category = "Laptop"
    elif "Tai nghe" in text or "Bass" in text or "Đeo" in text or "chống ồn" in text:
        category = "Tai nghe"
        
    sentiment = "NEUTRAL"
    if "tuyệt" in text or "mượt" in text or "trâu" in text or "đẹp" in text or "sướng" in text or "căng" in text or "êm" in text:
        sentiment = "POSITIVE"
    elif "hẻo" in text or "bệt" in text or "nóng" in text or "lỗi" in text or "ồn" in text or "ọp ẹp" in text or "sai" in text or "tuột" in text or "tịt" in text or "kém" in text:
        sentiment = "NEGATIVE"
        
    aspect = random.choice(ASPECTS[category])
    
    sentiment_results.append({
        "result_id": f"mock_r_{uuid.uuid4().hex[:12]}",
        "sentence_id": row.sentence_id,
        "comment_id": row.comment_id,
        "video_id": row.video_id,
        "aspect_label": aspect,
        "segment_text": row.sentence_text,
        "sentiment_label": sentiment,
        "confidence_score": round(random.uniform(0.8, 0.99), 4),
        "inference_model": "mock_generator",
        "dag_run_id": "mock_run",
        "processed_at": now
    })

print("Inserting sentiment results...")
chunk_size = 5000
for i in range(0, len(sentiment_results), chunk_size):
    chunk = sentiment_results[i:i+chunk_size]
    errors = client.insert_rows_json(f"{project}.{dataset}.raw_sentiment_results", chunk)
    if errors:
        print(f"Errors in chunk {i}: {errors}")
    else:
        print(f"Inserted {min(i+chunk_size, len(sentiment_results))}/{len(sentiment_results)}")

print("Done! You can now run `dbt run --select int_sentiment_results+`")
