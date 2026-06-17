import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

bq_client = bigquery.Client()

queries = [
    f"CREATE OR REPLACE TABLE `{project}.{dataset}.channel_config` AS SELECT * FROM `{project}.{dataset}.channel_config` WHERE channel_id NOT LIKE '%mock%'",
    f"CREATE OR REPLACE TABLE `{project}.{dataset}.raw_sentiment_results` AS SELECT * FROM `{project}.{dataset}.raw_sentiment_results` WHERE sentence_id NOT LIKE 'mock_%' AND result_id NOT LIKE 'mock_%'"
]

for q in queries:
    print(f"Executing: {q}")
    try:
        job = bq_client.query(q)
        job.result()
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

print("Native table cleanup completed.")
