import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')

datasets_to_check = [
    'sentiment_platform',
    'sentiment_platform_staging',
    'sentiment_platform_intermediate',
    'sentiment_platform_marts'
]

client = bigquery.Client(project=project_id)

for dataset_id in datasets_to_check:
    try:
        dataset_ref = client.dataset(dataset_id)
        dataset = client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_id} location: {dataset.location}")
    except Exception as e:
        print(f"Error checking {dataset_id}: {e}")
