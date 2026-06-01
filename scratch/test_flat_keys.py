import yt_dlp

url = "https://www.youtube.com/@tgddreview/videos"

ydl_opts = {
    'quiet': True,
    'extract_flat': True,
    'skip_download': True,
    'ignoreerrors': False,
    'extractor_args': {"youtubetab": ["skip=authcheck"]},
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info(url, download=False)

entries = result.get("entries") or []
if entries:
    print(f"Keys in entry: {list(entries[0].keys())}")
    print("Example entry:")
    import pprint
    pprint.pprint(entries[0])
