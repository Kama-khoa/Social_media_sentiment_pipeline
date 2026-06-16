import os
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

channel = {
    "channel_id": "UC_mock",
    "channel_name": "Kênh Đánh Giá Mock",
    "is_active": True,
    "is_historically_scanned": True,
    "last_updated_at": datetime.now().isoformat(),
    "created_at": datetime.now().isoformat()
}

errors = client.insert_rows_json(f"{project}.{dataset}.channel_config", [channel])
if errors:
    print(f"Errors: {errors}")
else:
    print("Inserted UC_mock into channel_config")
