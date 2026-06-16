import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')
bucket = os.environ.get('GCS_BUCKET_NAME')
partition_date = '2026-06-16'

query = f'''
ALTER TABLE `{project}.{dataset}.raw_videos`
ADD PARTITION (gcs_partition_date = '{partition_date}')
OPTIONS (uris=['gs://{bucket}/raw/youtube/{partition_date}/videos/*']);
'''
try:
    client.query(query).result()
    print('Partition added successfully!')
except Exception as e:
    print(f'Error: {e}')
