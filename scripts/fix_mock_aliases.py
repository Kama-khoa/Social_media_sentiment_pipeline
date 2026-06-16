import os
import uuid
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

print("Fetching mock products from product_config...")
query = f"""
    SELECT product_id, product_name
    FROM `{project}.{dataset}.product_config`
    WHERE product_id LIKE 'mock_%'
"""
rows = list(client.query(query).result())
print(f"Found {len(rows)} mock products.")

aliases_bq = []
now = datetime.now().isoformat()

for row in rows:
    # Just use the product_id as alias since the video title contains it
    aliases_bq.append({
        "alias_id": f"mock_a_{uuid.uuid4().hex[:12]}",
        "product_id": row.product_id,
        "alias_text": row.product_id,
        "is_active": True,
        "created_at": now
    })

print("Inserting aliases...")
chunk_size = 5000
for i in range(0, len(aliases_bq), chunk_size):
    chunk = aliases_bq[i:i+chunk_size]
    errors = client.insert_rows_json(f"{project}.{dataset}.product_aliases", chunk)
    if errors:
        print(f"Errors in chunk {i}: {errors}")
    else:
        print(f"Inserted {min(i+chunk_size, len(aliases_bq))}/{len(aliases_bq)}")

print("Done! You can now run `dbt run`")
