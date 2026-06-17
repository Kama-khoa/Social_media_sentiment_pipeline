import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Thêm project root vào python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from dotenv import load_dotenv
from google.cloud import bigquery

from elt.config import load_config
from elt.datacontext.gcs_client import GCSClient
from elt.extract.helpers.youtube_api_client import YouTubeApiClient
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.quota_repository import QuotaRepository

# Cấu hình log
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("extract_keyword_api")


def run_extract(keyword: str, max_results: int, force_keyword_match: str | None = None) -> None:
    load_dotenv()
    config = load_config()

    project_id = config.gcp.project_id
    dataset = config.gcp.dataset
    bucket_name = config.gcp.gcs_bucket

    logger.info(
        "Starting keyword video extract for: '%s' (max_results: %d)",
        keyword,
        max_results,
    )

    # Khởi tạo client
    bq_client = bigquery.Client(project=project_id)
    api_client = YouTubeApiClient(config.youtube_api_key)
    gcs_client = GCSClient(bucket_name, project_id)
    crawl_state_repo = CrawlStateRepository(bq_client, project_id, dataset)
    quota_repo = QuotaRepository(bq_client, project_id, dataset)

    # 1. Search video bằng YouTube API
    logger.info("Searching YouTube for keyword: '%s'", keyword)
    t_start = time.monotonic()
    raw_results = api_client.search_by_keyword(keyword, max_results=max_results)
    
    # 100 units cho search.list
    units_used = 100
    
    if not raw_results:
        logger.warning("No videos found for keyword: '%s'", keyword)
        return

    logger.info("Found %d video candidates from search", len(raw_results))
    video_ids = [item["id"] for item in raw_results]

    # 2. Enrich video details bằng videos.list
    logger.info("Enriching details for %d videos", len(video_ids))
    video_dtos = api_client.get_video_details(video_ids)
    
    # videos.list tiêu tốn 1 unit cho mỗi page 50 videos
    units_used += (len(video_ids) + 49) // 50

    if not video_dtos:
        logger.warning("Could not enrich details for any videos")
        return

    logger.info("Successfully enriched details for %d videos", len(video_dtos))

    # 3. Ghi đè keyword_matched nếu được yêu cầu (để map đúng với keyword_config)
    match_value = force_keyword_match or keyword
    logger.info("Setting keyword_matched to: '%s'", match_value)
    
    for dto in video_dtos:
        dto.keyword_matched = match_value
        dto.search_mode = "KEYWORD_SEARCH"

    # 4. Upload lên GCS (GCS-first)
    now = datetime.now(timezone.utc)
    gcs_path = GCSClient.build_videos_path(now)
    payload = [v.to_dict() for v in video_dtos]
    
    logger.info("Uploading %d videos to GCS path: %s", len(video_dtos), gcs_path)
    uri = gcs_client.upload_json(gcs_path, payload)
    logger.info("Uploaded raw videos data to GCS: %s", uri)

    # 5. Lưu vào BQ Crawl State (BQ-second)
    logger.info("Saving crawl state of %d videos to BigQuery", len(video_dtos))
    crawl_state_repo.bulk_upsert_from_video_dtos(video_dtos)
    logger.info("Successfully updated BigQuery crawl state")

    # 6. Ghi nhận log quota
    elapsed = time.monotonic() - t_start
    dag_run_id = f"manual-keyword-extract-{now.strftime('%Y%m%d%H%M%S')}"
    logger.info("Logging operation with %d quota units used", units_used)
    quota_repo.log_operation(
        operation_type="video_extraction_keyword",
        bucket="youtube_search",
        units_used=units_used,
        dag_run_id=dag_run_id,
        videos_processed=len(video_dtos),
        execution_time_seconds=elapsed,
    )
    quota_repo.upsert_daily_summary(now.date(), dag_run_id)
    logger.info("Extraction and ingestion completed successfully!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract YouTube videos by keyword directly using YouTube Data API")
    parser.add_argument("--keyword", type=str, default="iphone 16 pro")
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument(
        "--force-keyword-match", 
        type=str, 
        default="iPhone 16 Pro review",
        help="The keyword string that MUST match BQ keyword_config exactly to link the product"
    )
    args = parser.parse_args()

    run_extract(
        keyword=args.keyword,
        max_results=args.max_results,
        force_keyword_match=args.force_keyword_match,
    )


if __name__ == "__main__":
    main()
