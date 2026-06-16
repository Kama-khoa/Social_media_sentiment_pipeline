import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

job_config = bigquery.QueryJobConfig(use_query_cache=False)

try:
    query = f"SELECT COUNT(*) as count FROM `{project}.{dataset}.raw_videos` WHERE gcs_partition_date = '2026-06-17'"
    rows = list(client.query(query, job_config=job_config).result())
    print(f'Count of 2026-06-17 videos: {rows[0].count}')
except Exception as e:
    print(e)
