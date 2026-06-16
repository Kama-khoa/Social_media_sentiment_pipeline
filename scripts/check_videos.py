import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

try:
    query = f"SELECT COUNT(*) as count FROM `{project}.{dataset}.raw_videos`"
    rows = list(client.query(query).result())
    print(f'Count of all videos: {rows[0].count}')
except Exception as e:
    print(e)
