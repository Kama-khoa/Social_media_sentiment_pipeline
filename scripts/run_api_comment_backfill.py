from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from elt.config import load_config
from elt.extract.api_comment_backfill import ApiCommentBackfill
from elt.extract.helpers.youtube_api_comment_client import YouTubeApiCommentClient
from elt.quota_budget import QuotaBudget
from elt.repositories.api_comment_repository import ApiCommentRepository
from elt.repositories.quota_repository import QuotaRepository

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_api_comment_backfill")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill YouTube API comments into raw_comments_api.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-videos", type=int, default=None)
    parser.add_argument("--max-comments-per-video", type=int, default=None)
    parser.add_argument("--max-pages-per-video", type=int, default=None)
    parser.add_argument("--quota-units", type=int, default=None)
    parser.add_argument("--product-id", type=str, default=None, help="Filter candidate videos by product_id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    bq_client = bigquery.Client(project=config.gcp.project_id)
    comment_repo = ApiCommentRepository(bq_client, config.gcp.project_id, config.gcp.dataset)
    quota_repo = QuotaRepository(bq_client, config.gcp.project_id, config.gcp.dataset)
    used_by_bucket = quota_repo.get_today_used_by_bucket(date.today())
    budget = QuotaBudget.from_config(config, used_by_bucket)
    logger.info("Quota budget: %s", budget)
    comment_client = YouTubeApiCommentClient(config.youtube_api_key)
    runner = ApiCommentBackfill(config, comment_client, comment_repo, quota_repo)
    dag_run_id = args.run_id or (
        f"api_comment_backfill__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        f"__{uuid.uuid4().hex[:8]}"
    )

    result = runner.run(
        dag_run_id=dag_run_id,
        max_videos=args.max_videos,
        max_comments_per_video=args.max_comments_per_video,
        max_pages_per_video=args.max_pages_per_video,
        quota_units=args.quota_units,
        budget=budget,
        dry_run=args.dry_run,
        product_id=args.product_id,
    )
    quota_repo.upsert_daily_summary(date.today(), dag_run_id)
    logger.info("API comment backfill result: %s", result)


if __name__ == "__main__":
    main()
