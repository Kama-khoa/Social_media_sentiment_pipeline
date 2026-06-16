import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

try:
    query = f"SELECT video_id FROM `{project}.{dataset}.raw_videos` WHERE gcs_partition_date = '2026-06-16' LIMIT 10"
    rows = list(client.query(query).result())
    for row in rows:
        print(row.video_id)
except Exception as e:
    print(e)
