import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
storage_client = storage.Client()
source_bucket = storage_client.bucket('social-media-sentiment-raw')
target_bucket = storage_client.bucket('product-sentiment-raw-1806')

blobs = source_bucket.list_blobs(prefix='raw/youtube/2026-06-17/videos/mock_videos.json')
for blob in blobs:
    print(f'Copying {blob.name} to product-sentiment-raw-1806...')
    source_bucket.copy_blob(blob, target_bucket, 'raw/youtube/2026-06-17/videos/mock_videos.json')

blobs_comments = source_bucket.list_blobs(prefix='raw/youtube/2026-06-16/comments/')
for blob in blobs_comments:
    if 'mock' in blob.name:
        source_bucket.copy_blob(blob, target_bucket, blob.name)

print('Copy completed!')
