from google.cloud import bigquery
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = bigquery.Client(project=os.getenv('GCP_PROJECT_ID'))
dataset = os.getenv('BQ_DATASET')

query = f"""
    SELECT
        p.product_id,
        p.product_name,
        COUNT(DISTINCT m.video_id) as video_count,
        SUM(v.comment_count) as total_comments
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
    JOIN `{os.getenv('GCP_PROJECT_ID')}.{dataset}_intermediate.int_video_product_mentions` m ON p.product_id = m.product_id
    JOIN `{os.getenv('GCP_PROJECT_ID')}.{dataset}_staging.stg_youtube_videos` v ON m.video_id = v.video_id
    WHERE p.category IN ('Điện thoại', 'smartphone')
    GROUP BY p.product_id, p.product_name
    ORDER BY total_comments DESC
    LIMIT 10
"""
results = []
for row in client.query(query):
    results.append({'id': row.product_id, 'name': row.product_name, 'video_count': row.video_count, 'total_comments': row.total_comments})

with open('top_phones_out.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
