import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
storage_client = storage.Client()
bucket = storage_client.bucket('social-media-sentiment-raw')

# move mock videos
blobs = bucket.list_blobs(prefix='raw/youtube/2026-06-16/videos/')
for blob in blobs:
    if 'mock' in blob.name:
        new_name = blob.name.replace('raw/youtube/2026-06-16/videos/', 'raw/videos/2026/06/16/')
        print(f"Moving {blob.name} to {new_name}")
        bucket.copy_blob(blob, bucket, new_name)
        # We can delete original later

# move mock comments
blobs = bucket.list_blobs(prefix='raw/youtube/2026-06-16/comments/')
for blob in blobs:
    if 'mock' in blob.name:
        new_name = blob.name.replace('raw/youtube/2026-06-16/comments/', 'raw/comments/2026/06/16/')
        print(f"Moving {blob.name} to {new_name}")
        bucket.copy_blob(blob, bucket, new_name)
