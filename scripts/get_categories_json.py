from google.cloud import bigquery
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = bigquery.Client(project=os.getenv('GCP_PROJECT_ID'))
dataset = os.getenv('BQ_DATASET')

query = f"""
    SELECT DISTINCT category
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
"""
categories = []
for row in client.query(query):
    categories.append(row.category)

query2 = f"""
    SELECT p.product_id, p.product_name, p.category
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
    LIMIT 20
"""
products = []
for row in client.query(query2):
    products.append({'id': row.product_id, 'name': row.product_name, 'category': row.category})

out = {'categories': categories, 'products': products}
with open('categories_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
