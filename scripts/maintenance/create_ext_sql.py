import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
dataset_id = os.environ.get('BQ_DATASET')
bucket_name = os.environ.get('GCS_BUCKET_NAME')

client = bigquery.Client(project=project_id)

def create_external_table_sql(table_name, gcs_prefix):
    sql = f"""
    CREATE OR REPLACE EXTERNAL TABLE `{project_id}.{dataset_id}.{table_name}`
    OPTIONS (
      format = 'JSON',
      uris = ['gs://{bucket_name}/{gcs_prefix}']
    );
    """
    try:
        query_job = client.query(sql)
        query_job.result()
        print(f"Created external table {table_name} using JSON format.")
    except Exception as e:
        print(f"Error creating {table_name}: {e}")

create_external_table_sql("raw_videos", "raw/videos/*")
create_external_table_sql("raw_comments", "raw/comments/*")
