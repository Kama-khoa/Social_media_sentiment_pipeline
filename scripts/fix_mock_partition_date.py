import os
import json
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
storage_client = storage.Client()
bucket = storage_client.bucket('social-media-sentiment-raw')

# fix mock videos
blobs = bucket.list_blobs(prefix='raw/videos/2026/06/16/')
for blob in blobs:
    if 'mock' in blob.name:
        content = blob.download_as_text()
        lines = content.strip().split('\n')
        new_lines = []
        for line in lines:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if 'gcs_partition_date' in data:
                    data['gcs_partition_date'] = data['gcs_partition_date'].replace('-', '/')
                new_lines.append(json.dumps(data, ensure_ascii=False))
            except Exception as e:
                print(f"Error parsing line: {e}")
                new_lines.append(line)
        
        blob.upload_from_string('\n'.join(new_lines) + '\n', content_type='application/json')
        print(f"Fixed {blob.name}")

# fix mock comments
blobs = bucket.list_blobs(prefix='raw/comments/2026/06/16/')
for blob in blobs:
    if 'mock' in blob.name:
        content = blob.download_as_text()
        lines = content.strip().split('\n')
        new_lines = []
        for line in lines:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if 'gcs_partition_date' in data:
                    data['gcs_partition_date'] = data['gcs_partition_date'].replace('-', '/')
                new_lines.append(json.dumps(data, ensure_ascii=False))
            except Exception as e:
                print(f"Error parsing line: {e}")
                new_lines.append(line)
        
        blob.upload_from_string('\n'.join(new_lines) + '\n', content_type='application/json')
        print(f"Fixed {blob.name}")
