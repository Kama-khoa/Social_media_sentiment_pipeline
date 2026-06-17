import os
from google.cloud import storage, bigquery
from dotenv import load_dotenv

load_dotenv()

project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

# 1. Delete GCS Blobs
storage_client = storage.Client()
bucket = storage_client.bucket('social-media-sentiment-raw')

prefixes = ['raw/videos/2026/06/16/', 'raw/comments/2026/06/16/', 'raw/youtube/']
for prefix in prefixes:
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if 'mock' in blob.name:
            print(f"Deleting GCS blob: {blob.name}")
            blob.delete()

# 2. Delete Native BigQuery Data
bq_client = bigquery.Client()

queries = [
    f"DELETE FROM `{project}.{dataset}.channel_config` WHERE channel_id LIKE '%mock%'",
    f"DELETE FROM `{project}.{dataset}.raw_sentiment_results` WHERE sentence_id LIKE 'mock_%' OR result_id LIKE 'mock_%'"
]

for q in queries:
    print(f"Executing: {q}")
    try:
        job = bq_client.query(q)
        job.result()
        print(f"Deleted {job.num_dml_affected_rows} rows.")
    except Exception as e:
        print(f"Error: {e}")

print("Cleanup completed for GCS and native tables.")
