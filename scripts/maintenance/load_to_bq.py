import os
import json
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud import storage
import pandas as pd

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
dataset_id = os.environ.get('BQ_DATASET')
bucket_name = os.environ.get('GCS_BUCKET_NAME')

bq_client = bigquery.Client(project=project_id)
storage_client = storage.Client(project=project_id)
bucket = storage_client.bucket(bucket_name)

def load_prefix_to_table(prefix, table_name):
    blobs = list(bucket.list_blobs(prefix=prefix))
    all_data = []
    for blob in blobs:
        if blob.name.endswith('.json'):
            try:
                content = blob.download_as_string()
                data = json.loads(content)
                if isinstance(data, list):
                    all_data.extend(data)
                elif isinstance(data, dict):
                    all_data.append(data)
            except Exception as e:
                print(f"Error reading {blob.name}: {e}")
                
    if all_data:
        df = pd.DataFrame(all_data)
        
        # Convert objects to string to avoid BigQuery type inference issues
        for col in df.columns:
            if df[col].dtype == 'object':
                # Convert complex objects (dict, list) to JSON strings
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
        
        table_id = f"{project_id}.{dataset_id}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True
        )
        job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        print(f"Loaded {len(all_data)} rows into {table_id}")
    else:
        print(f"No data found for {prefix}")

load_prefix_to_table("raw/videos/", "raw_videos")
load_prefix_to_table("raw/comments/", "raw_comments")
