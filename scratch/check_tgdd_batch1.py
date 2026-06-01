import os
from dotenv import load_dotenv
from google.cloud import bigquery
from datetime import datetime, timezone, timedelta
from elt.config import load_config
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpVideoFetcher
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.keyword_repository import KeywordRepository

load_dotenv()
project_id = os.environ.get('GCP_PROJECT_ID')
dataset_id = os.environ.get('BQ_DATASET')

client = bigquery.Client(project=project_id)
config = load_config()

# Mock channel DTO for TGDD
class MockChannel:
    channel_id = "UClAoXGpwSi4bgwBLuZKxsnQ"
    channel_name = "Thế Giới Di Động"
    channel_url = "https://www.youtube.com/@tgddreview"

ch = MockChannel()
url = ch.channel_url

keyword_repo = KeywordRepository(client, project_id, dataset_id)
crawl_state_repo = CrawlStateRepository(client, project_id, dataset_id)

keywords = keyword_repo.get_active_keywords()
fetcher = YtdlpVideoFetcher(keywords)

print("Fetching channel videos (flat scan)...")
raw = fetcher.fetch_channel_videos(url, max_results=300)
print(f"Total raw videos: {len(raw)}")

# Filter
filtered_raw = [v for v in raw] # No date cutoff since dates are None
matched = fetcher.filter_by_keywords(filtered_raw)
print(f"Total matched videos: {len(matched)}")

existing_ids = crawl_state_repo.get_existing_video_ids(ch.channel_id)
remaining = [v for v in matched if v["id"] not in existing_ids]
print(f"Total remaining videos: {len(remaining)}")

batch_size = 30
batch = remaining[:batch_size]
print(f"\nEnriching first batch ({len(batch)} videos)...")
enriched = fetcher.enrich_batch(batch)
dtos = fetcher.build_video_dtos(enriched, ch.channel_id, search_mode="MODE0")

cutoff_date = datetime.now(timezone.utc) - timedelta(days=730)
print(f"Cutoff date: {cutoff_date}")

recent_dtos = [dto for dto in dtos if dto.published_at >= cutoff_date]
print(f"Total dtos: {len(dtos)}")
print(f"Total recent dtos: {len(recent_dtos)}")

for i, dto in enumerate(dtos):
    title_safe = dto.title.encode('ascii', 'ignore').decode('ascii')
    print(f"[{i+1}] ID: {dto.video_id} | Date: {dto.published_at} | Recent: {dto.published_at >= cutoff_date} | Title: {title_safe}")
