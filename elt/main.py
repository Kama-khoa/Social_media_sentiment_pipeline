from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from google.cloud import bigquery

from elt.config import load_config
from elt.datacontext.gcs_client import GCSClient
from elt.extract.comment_extractor import CommentExtractor
from elt.extract.helpers.comment_downloader import ProxyConfig
from elt.extract.video_extractor import VideoExtractor
from elt.quota_budget import QuotaBudget
from elt.repositories.channel_repository import ChannelRepository
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.keyword_repository import KeywordRepository
from elt.repositories.quota_repository import QuotaRepository

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("elt.main")


def _build_bq_client(config) -> bigquery.Client:
    return bigquery.Client(project=config.gcp.project_id)


def _build_repositories(bq_client: bigquery.Client, config):
    project_id = config.gcp.project_id
    dataset = config.gcp.dataset
    return {
        "channel_repo": ChannelRepository(bq_client, project_id, dataset),
        "keyword_repo": KeywordRepository(bq_client, project_id, dataset),
        "crawl_state_repo": CrawlStateRepository(bq_client, project_id, dataset),
        "quota_repo": QuotaRepository(bq_client, project_id, dataset),
    }


def _build_proxy_config(config) -> ProxyConfig | None:
    try:
        return ProxyConfig(
            host=config.brightdata_proxy_host,
            port=int(config.brightdata_proxy_port),
            username=config.brightdata_username,
            password=config.brightdata_password,
        )
    except (ValueError, AttributeError):
        logger.warning("BrightData proxy not configured, running without proxy")
        return None


def _build_quota_budget(config, quota_repo: QuotaRepository) -> QuotaBudget:
    today = date.today()
    already_used = quota_repo.get_today_used_by_bucket(today)
    budget = QuotaBudget.from_config(config, already_used)
    logger.info("Quota budget: %s", budget)
    return budget


def run_videos(config, repos: dict, gcs_client: GCSClient, dag_run_id: str, execution_date: str):
    budget = _build_quota_budget(config, repos["quota_repo"])

    extractor = VideoExtractor(
        config=config,
        channel_repo=repos["channel_repo"],
        keyword_repo=repos["keyword_repo"],
        crawl_state_repo=repos["crawl_state_repo"],
        quota_repo=repos["quota_repo"],
        gcs_client=gcs_client,
    )

    logger.info("=== VIDEO EXTRACTION START ===")
    result = extractor.run(execution_date, dag_run_id, budget)
    logger.info("=== VIDEO EXTRACTION DONE === %s", result)
    return result


def run_comments(config, repos: dict, gcs_client: GCSClient, dag_run_id: str):
    proxy_config = _build_proxy_config(config)

    extractor = CommentExtractor(
        config=config,
        crawl_state_repo=repos["crawl_state_repo"],
        quota_repo=repos["quota_repo"],
        gcs_client=gcs_client,
        proxy_config=proxy_config,
    )

    logger.info("=== COMMENT EXTRACTION START ===")
    result = extractor.run(dag_run_id)
    logger.info("=== COMMENT EXTRACTION DONE === %s", result)
    return result


def run_full(config, repos: dict, gcs_client: GCSClient, dag_run_id: str, execution_date: str):
    video_result = run_videos(config, repos, gcs_client, dag_run_id, execution_date)
    comment_result = run_comments(config, repos, gcs_client, dag_run_id)

    repos["quota_repo"].upsert_daily_summary(date.today(), dag_run_id)
    logger.info("=== DAILY SUMMARY UPSERTED ===")

    return {"videos": video_result, "comments": comment_result}


def main():
    parser = argparse.ArgumentParser(description="ELT Extraction Pipeline — Manual Runner")
    parser.add_argument(
        "--mode",
        choices=["videos", "comments", "full"],
        default="full",
        help="videos = video discovery only, comments = comment crawl only, full = both (default)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Execution date in YYYY-MM-DD format (default: today UTC)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to pipeline_config.yaml (default: config/pipeline_config.yaml)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom DAG run ID (default: auto-generated)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    bq_client = _build_bq_client(config)
    repos = _build_repositories(bq_client, config)
    gcs_client = GCSClient(config.gcp.gcs_bucket, config.gcp.project_id)

    dag_run_id = args.run_id or f"manual__{args.date}T{datetime.now(timezone.utc).strftime('%H%M%S')}__{uuid.uuid4().hex[:8]}"
    execution_date = args.date

    logger.info("Pipeline config loaded")
    logger.info("Mode: %s | Date: %s | Run ID: %s", args.mode, execution_date, dag_run_id)

    if args.mode == "videos":
        run_videos(config, repos, gcs_client, dag_run_id, execution_date)
    elif args.mode == "comments":
        run_comments(config, repos, gcs_client, dag_run_id)
    else:
        run_full(config, repos, gcs_client, dag_run_id, execution_date)

    logger.info("Pipeline finished")


if __name__ == "__main__":
    main()
