import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project_id = os.environ['GCP_PROJECT_ID']
dataset = os.environ['BQ_DATASET']

table_ref = f"{project_id}.{dataset}.product_detail_change_requests"
q = f"""
SELECT * FROM `{table_ref}`
WHERE status = @status
ORDER BY created_at DESC
"""
print("Query:\n", q)
job_config = bigquery.QueryJobConfig(
    query_parameters=[bigquery.ScalarQueryParameter('status', 'STRING', 'pending')]
)
try:
    client.query(q, job_config=job_config).result()
    print('OK product_detail_change_requests')
except Exception as e:
    print(f'ERROR product_detail_change_requests: {e}')

table_ref2 = f"{project_id}.{dataset}.keyword_config"
q2 = f"""
SELECT * FROM `{table_ref2}`
WHERE 1=1
ORDER BY created_at DESC
LIMIT 50
"""
try:
    client.query(q2).result()
    print('OK keyword_config')
except Exception as e:
    print(f'ERROR keyword_config: {e}')
