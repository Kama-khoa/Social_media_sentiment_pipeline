from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()
client = bigquery.Client(project=os.getenv('GCP_PROJECT_ID'))
dataset = os.getenv('BQ_DATASET')

query = f"""
    SELECT DISTINCT category
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
"""
results = []
for row in client.query(query):
    results.append(row.category)

print(f'Categories: {results}')

query = f"""
    SELECT p.product_id, p.product_name, p.category
    FROM `{os.getenv('GCP_PROJECT_ID')}.{dataset}_marts.dim_products` p
    LIMIT 20
"""
for row in client.query(query):
    print(f'{row.product_id}: {row.product_name} - {row.category}')
