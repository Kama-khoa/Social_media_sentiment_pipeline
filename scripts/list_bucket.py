import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
storage_client = storage.Client()
bucket_name = os.environ.get('GCS_BUCKET_NAME')
bucket = storage_client.bucket(bucket_name)

blobs = bucket.list_blobs(prefix='raw/youtube/2026-06-16/videos/')
found = False
for blob in blobs:
    print(blob.name, blob.size)
    found = True

if not found:
    print("No blobs found in that prefix!")
