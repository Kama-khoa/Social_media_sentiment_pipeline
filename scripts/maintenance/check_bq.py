import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
print(f"Project ID: {project_id}")

try:
    client = bigquery.Client(project=project_id)
    datasets = list(client.list_datasets())
    if datasets:
        print("Datasets in project:")
        for dataset in datasets:
            print(f"- {dataset.dataset_id}")
    else:
        print(f"Project {project_id} does not contain any datasets.")
        
    dataset_id = os.environ.get('BQ_DATASET')
    dataset_ref = client.dataset(dataset_id)
    try:
        dataset = client.get_dataset(dataset_ref)
        print(f"\nDataset {dataset_id} exists. Tables:")
        tables = list(client.list_tables(dataset))
        if tables:
            for table in tables:
                print(f"- {table.table_id}")
        else:
            print("  No tables found.")
    except Exception as e:
        print(f"\nDataset {dataset_id} does not exist or access denied: {e}")

except Exception as e:
    print(f"Error connecting to BigQuery: {e}")
