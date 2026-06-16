import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
storage_client = storage.Client()
bucket = storage_client.bucket('social-media-sentiment-raw')

print("Blobs in raw/videos/:")
blobs = bucket.list_blobs(prefix='raw/videos/')
for blob in blobs:
    print(blob.name)

print("\nBlobs in raw/youtube/:")
blobs = bucket.list_blobs(prefix='raw/youtube/')
count = 0
for blob in blobs:
    print(blob.name)
    count += 1
    if count > 10:
        print("... and more")
        break
