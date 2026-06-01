import yt_dlp
from datetime import datetime, timezone, timedelta

# Calculate date 180 days ago: YYYYMMDD
date_limit = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y%m%d")
print(f"Date limit (dateafter): {date_limit}")

url = "https://www.youtube.com/@tgddreview/videos"

ydl_opts = {
    'quiet': True,
    'extract_flat': True,
    'skip_download': True,
    'ignoreerrors': False,
    'extractor_args': {"youtubetab": ["skip=authcheck"]},
    'dateafter': date_limit,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info(url, download=False)

entries = result.get("entries") or []
print(f"Total entries fetched: {len(entries)}")

for i, entry in enumerate(entries[:5]):
    print(f"[{i+1}] ID: {entry.get('id')} | Title: {entry.get('title')} | Date: {entry.get('upload_date')}")
