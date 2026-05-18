import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')

datasets_to_delete = [
    'sentiment_platform_staging',
    'sentiment_platform_intermediate',
    'sentiment_platform_marts'
]

client = bigquery.Client(project=project_id)

for dataset_id in datasets_to_delete:
    try:
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        print(f"Deleted dataset {dataset_id}")
    except Exception as e:
        print(f"Error deleting {dataset_id}: {e}")
