import yt_dlp
from datetime import datetime, timezone

video_id = "4Ov5fcnNH5M"
url = f"https://www.youtube.com/watch?v={video_id}"

ydl_opts = {
    'quiet': True,
    'skip_download': True,
    'ignoreerrors': False,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    entry = ydl.extract_info(url, download=False)

print(f"ID: {entry.get('id')}")
title_safe = entry.get('title', '').encode('ascii', 'ignore').decode('ascii')
print(f"Title: {title_safe}")
print(f"upload_date: {entry.get('upload_date')} (type: {type(entry.get('upload_date'))})")
print(f"timestamp: {entry.get('timestamp')} (type: {type(entry.get('timestamp'))})")
print(f"release_timestamp: {entry.get('release_timestamp')} (type: {type(entry.get('release_timestamp'))})")
print(f"release_date: {entry.get('release_date')} (type: {type(entry.get('release_date'))})")

# Let's run the parser
def _parse_published_at(entry: dict) -> datetime | None:
    published_at = entry.get("published_at")
    if isinstance(published_at, datetime):
        if published_at.tzinfo is None:
            return published_at.replace(tzinfo=timezone.utc)
        return published_at

    timestamp = entry.get("timestamp")
    if timestamp:
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            pass

    upload_date = entry.get("upload_date")
    if upload_date:
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None

parsed = _parse_published_at(entry)
print(f"Parsed datetime: {parsed}")
