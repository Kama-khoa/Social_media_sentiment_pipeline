import os
import json
import sys
from dotenv import load_dotenv
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
bucket_name = os.environ.get('GCS_BUCKET_NAME')

client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)

def process_blob(blob):
    if not blob.name.endswith('.json'):
        return False
    try:
        content = blob.download_as_string()
        if content.strip().startswith(b'['):
            data = json.loads(content)
            if isinstance(data, list):
                ndjson_content = "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
                blob.upload_from_string(ndjson_content, content_type="application/x-ndjson")
                return True
    except Exception as e:
        print(f"Error on {blob.name}: {e}", file=sys.stderr)
    return False

def fix_json_array(prefix):
    print(f"Listing files in {prefix}...", flush=True)
    blobs = list(bucket.list_blobs(prefix=prefix))
    print(f"Found {len(blobs)} files in {prefix}. Starting conversion...", flush=True)
    
    count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_blob, blob): blob for blob in blobs}
        for i, future in enumerate(as_completed(futures), 1):
            if future.result():
                count += 1
            if i % 50 == 0:
                print(f"Processed {i}/{len(blobs)} files. Fixed {count} so far...", flush=True)
                
    print(f"Finished fixing {count} out of {len(blobs)} files in {prefix}", flush=True)

fix_json_array("raw/videos/")
fix_json_array("raw/comments/")
