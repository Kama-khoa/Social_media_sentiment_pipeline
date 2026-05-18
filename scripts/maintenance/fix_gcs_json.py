import os
import json
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
bucket_name = os.environ.get('GCS_BUCKET_NAME')

client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)

def fix_json_array(prefix):
    blobs = list(bucket.list_blobs(prefix=prefix))
    count = 0
    for blob in blobs:
        if blob.name.endswith('.json'):
            try:
                content = blob.download_as_string()
                # Simple check if it's a JSON array
                if content.strip().startswith(b'['):
                    data = json.loads(content)
                    if isinstance(data, list):
                        ndjson_content = "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
                        blob.upload_from_string(ndjson_content, content_type="application/x-ndjson")
                        count += 1
                        print(f"Fixed {blob.name}")
            except Exception as e:
                print(f"Error on {blob.name}: {e}")
    print(f"Finished fixing {count} files in {prefix}")

fix_json_array("raw/videos/")
fix_json_array("raw/comments/")
