import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client()
project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET')

queries = [
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}.product_config`',
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}.product_details`',
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}.raw_sentiment_results`',
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}_marts.dim_products`',
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}_marts.fact_product_mentions`',
    f'SELECT COUNT(*) as count FROM `{project}.{dataset}_marts.agg_daily_product_ranking`'
]

tables = [
    'product_config',
    'product_details',
    'raw_sentiment_results',
    'dim_products',
    'fact_product_mentions',
    'agg_daily_product_ranking'
]

print('--- BIGQUERY DATASET COUNTS ---')
for table, query in zip(tables, queries):
    try:
        rows = list(client.query(query).result())
        print(f'{table}: {rows[0].count} rows')
    except Exception as e:
        print(f'{table}: Error - {e}')
