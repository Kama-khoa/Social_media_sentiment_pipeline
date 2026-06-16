import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')
bucket = os.environ.get('GCS_BUCKET_NAME')

external_config = bigquery.ExternalConfig('NEWLINE_DELIMITED_JSON')
external_config.source_uris = [f'gs://{bucket}/raw/youtube/2026-06-16/videos/videos_run_mock.json']
external_config.autodetect = True

table = bigquery.Table(f'{project}.{dataset}.test_raw_videos')
table.external_data_configuration = external_config

try:
    client.delete_table(table, not_found_ok=True)
    table = client.create_table(table)
    query = f'SELECT COUNT(*) as count FROM `{project}.{dataset}.test_raw_videos`'
    rows = list(client.query(query).result())
    print(f'Count from test table: {rows[0].count}')
except Exception as e:
    print(e)
