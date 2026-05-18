import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
dataset_id = os.environ.get('BQ_DATASET')
bucket_name = os.environ.get('GCS_BUCKET_NAME')

client = bigquery.Client(project=project_id)

def create_external_table(table_name, gcs_prefix):
    table_id = f"{project_id}.{dataset_id}.{table_name}"
    
    external_config = bigquery.ExternalConfig("NEWLINE_DELIMITED_JSON")
    external_config.source_uris = [f"gs://{bucket_name}/{gcs_prefix}"]
    external_config.autodetect = True
    # Ignore unknown values for flexible JSON parsing
    external_config.ignore_unknown_values = True
    
    table = bigquery.Table(table_id)
    table.external_data_configuration = external_config
    
    try:
        # Delete table if exists
        client.delete_table(table_id, not_found_ok=True)
        # Create external table
        table = client.create_table(table)
        print(f"Created external table {table_id}")
    except Exception as e:
        print(f"Error creating {table_name}: {e}")

create_external_table("raw_videos", "raw/videos/*")
create_external_table("raw_comments", "raw/comments/*")
