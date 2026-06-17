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
        p.category
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
    WHERE p.category = 'Smartphone'
    LIMIT 20
"""
results = []
for row in client.query(query):
    results.append({'id': row.product_id, 'name': row.product_name, 'category': row.category})

with open('products_out.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Exported {len(results)} products to products_out.json")
