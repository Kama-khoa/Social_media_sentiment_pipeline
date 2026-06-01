import yt_dlp
from datetime import datetime, timezone, timedelta

url = "https://www.youtube.com/@tgddreview/videos"

ydl_opts = {
    'quiet': True,
    'extract_flat': True,
    'skip_download': True,
    'ignoreerrors': False,
    'extractor_args': {"youtubetab": ["skip=authcheck"]},
    'playlistend': 50,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info(url, download=False)

entries = result.get("entries") or []
print(f"Total entries fetched: {len(entries)}")

for i, entry in enumerate(entries[:10]):
    print(f"\n[{i+1}] ID: {entry.get('id')}")
    print(f"    Title: {entry.get('title')}")
    print(f"    Upload Date: {entry.get('upload_date')}")
    print(f"    Timestamp: {entry.get('timestamp')}")
