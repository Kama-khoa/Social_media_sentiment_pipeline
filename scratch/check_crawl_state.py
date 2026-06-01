import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
dataset_id = os.environ.get('BQ_DATASET')

client = bigquery.Client(project=project_id)

def check_channel(channel_name):
    # Get channel_id
    query = f"""
        SELECT channel_id, channel_name, is_historically_scanned, historical_scan_completed_at
        FROM `{project_id}.{dataset_id}.channel_config`
        WHERE channel_name LIKE '%{channel_name}%'
    """
    rows = list(client.query(query).result())
    if not rows:
        print(f"Channel not found: {channel_name}")
        return
    
    ch = rows[0]
    channel_id = ch.channel_id
    ch_name = ch.channel_name.encode('ascii', 'ignore').decode('ascii')
    print(f"\n=== Channel: {ch_name} ({channel_id}) ===")
    print(f"is_historically_scanned: {ch.is_historically_scanned}")
    print(f"historical_scan_completed_at: {ch.historical_scan_completed_at}")

    # Check count in video_crawl_state
    query_state = f"""
        SELECT COUNT(*) as cnt, MIN(published_at) as min_pub, MAX(published_at) as max_pub
        FROM `{project_id}.{dataset_id}.video_crawl_state`
        WHERE channel_id = '{channel_id}'
    """
    state_rows = list(client.query(query_state).result())
    if state_rows:
        row = state_rows[0]
        print(f"video_crawl_state: {row.cnt} videos, min_pub: {row.min_pub}, max_pub: {row.max_pub}")
    else:
        print("No videos found in video_crawl_state")

check_channel("Tinh tế")
check_channel("Thế Giới Di Động")
check_channel("relab")
