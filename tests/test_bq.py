import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
dataset = os.environ.get("BQ_DATASET", "sentiment_platform")

print("--- Quota Daily Summary ---")
query = f"SELECT * FROM `{os.environ.get('GCP_PROJECT_ID')}.{dataset}.quota_daily_summary` ORDER BY 1 DESC LIMIT 5"
try:
    for row in client.query(query).result():
        print(dict(row))
except Exception as e:
    print(e)

print("\n--- Raw Sentiment Results Schema ---")
query = f"SELECT column_name, data_type FROM `{os.environ.get('GCP_PROJECT_ID')}.{dataset}.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = 'raw_sentiment_results'"
try:
    for row in client.query(query).result():
        print(dict(row))
except Exception as e:
    print(e)
