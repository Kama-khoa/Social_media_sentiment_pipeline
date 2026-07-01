from __future__ import annotations

import argparse
import logging
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
from elt.seed_data.seed_loader import sync_channels, sync_keywords, sync_product_spec_templates, sync_products

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


def _build_video_extractor(config, repos: dict, gcs_client: GCSClient) -> VideoExtractor:
    return VideoExtractor(
        config=config,
        channel_repo=repos["channel_repo"],
        keyword_repo=repos["keyword_repo"],
        crawl_state_repo=repos["crawl_state_repo"],
        quota_repo=repos["quota_repo"],
        gcs_client=gcs_client,
    )


def _build_comment_extractor(config, repos: dict, gcs_client: GCSClient) -> CommentExtractor:
    proxy_config = _build_proxy_config(config)
    return CommentExtractor(
        config=config,
        crawl_state_repo=repos["crawl_state_repo"],
        quota_repo=repos["quota_repo"],
        gcs_client=gcs_client,
        proxy_config=proxy_config,
    )


def _sync_seed_data(bq_client: bigquery.Client) -> None:
    logger.info("=== SEED SYNC ===")

    ch_result = sync_channels(bq_client)
    if ch_result["new"] > 0:
        logger.info(
            "Seed sync: %d new channels synced (CSV: %d, new: %d)",
            ch_result["synced"], ch_result["csv_total"], ch_result["new"],
        )
    else:
        logger.info("Seed sync: channels up to date (%d in CSV)", ch_result["csv_total"])

    kw_result = sync_keywords(bq_client)
    logger.info("Seed sync: %d keywords synced (CSV: %d)", kw_result["synced"], kw_result["csv_total"])

    product_result = sync_products(bq_client)
    logger.info(
        "Seed sync: %d canonical products and %d aliases synced",
        product_result["products"], product_result["aliases"],
    )
    logger.info("Seed sync: %d product specification templates synced", sync_product_spec_templates(bq_client))


def run_videos(config, repos: dict, gcs_client: GCSClient, dag_run_id: str, execution_date: str):
    budget = _build_quota_budget(config, repos["quota_repo"])
    extractor = _build_video_extractor(config, repos, gcs_client)

    logger.info("=== VIDEO EXTRACTION START ===")

    # daily_result = 0
    daily_result = extractor.run_daily(execution_date, dag_run_id, budget)
    logger.info("Phase A done: %s", daily_result)

    historical_result = extractor.run_historical(execution_date, dag_run_id, budget)
    logger.info("Phase B done: %s", historical_result)

    logger.info("=== VIDEO EXTRACTION DONE ===")
    return {"daily": daily_result, "historical": historical_result}


def run_comments(config, repos: dict, gcs_client: GCSClient, dag_run_id: str):
    extractor = _build_comment_extractor(config, repos, gcs_client)

    logger.info("=== COMMENT EXTRACTION START ===")
    result = extractor.run_backlog(dag_run_id)
    logger.info("=== COMMENT EXTRACTION DONE === %s", result)
    return result


def run_full(config, repos: dict, gcs_client: GCSClient, dag_run_id: str, execution_date: str):
    budget = _build_quota_budget(config, repos["quota_repo"])
    video_extractor = _build_video_extractor(config, repos, gcs_client)
    comment_extractor = _build_comment_extractor(config, repos, gcs_client)

    logger.info("=== PHASE A: DAILY ===")
    # daily_result = 0
    daily_result = video_extractor.run_daily(
        execution_date, dag_run_id, budget,
        comment_extractor=comment_extractor,
    )
    logger.info("Phase A done: %s", daily_result)

    logger.info("=== PHASE B: HISTORICAL ===")
    historical_result = video_extractor.run_historical(
        execution_date, dag_run_id, budget,
        comment_extractor=comment_extractor,
    )
    logger.info("Phase B done: %s", historical_result)

    logger.info("=== PHASE C: BACKLOG ===")
    backlog_result = comment_extractor.run_backlog(dag_run_id)
    logger.info("Phase C done: %s", backlog_result)

    repos["quota_repo"].upsert_daily_summary(date.today(), dag_run_id)
    logger.info("=== PIPELINE DONE ===")

    return {
        "daily": daily_result,
        "historical": historical_result,
        "backlog": backlog_result,
    }


def run_manual_channel(
    config,
    repos: dict,
    gcs_client: GCSClient,
    dag_run_id: str,
    execution_date: str,
    channel_id: str,
    lookback_days: int,
    crawl_mode: str,
):
    budget = _build_quota_budget(config, repos["quota_repo"])
    video_extractor = _build_video_extractor(config, repos, gcs_client)
    comment_extractor = _build_comment_extractor(config, repos, gcs_client)

    logger.info(
        "=== MANUAL CHANNEL CRAWL START === channel_id=%s lookback_days=%s crawl_mode=%s",
        channel_id,
        lookback_days,
        crawl_mode,
    )
    result = video_extractor.run_manual_channel(
        channel_id=channel_id,
        lookback_days=lookback_days,
        crawl_mode=crawl_mode,
        execution_date=execution_date,
        dag_run_id=dag_run_id,
        budget=budget,
        comment_extractor=comment_extractor,
    )
    repos["quota_repo"].upsert_daily_summary(date.today(), dag_run_id)
    logger.info("=== MANUAL CHANNEL CRAWL DONE === %s", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="ELT Extraction Pipeline")
    parser.add_argument(
        "--mode",
        choices=["videos", "comments", "full"],
        default="full",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--manual-channel-id",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--crawl-mode",
        choices=["api_or_ytdlp", "ytdlp"],
        default="api_or_ytdlp",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    bq_client = _build_bq_client(config)
    _sync_seed_data(bq_client)
    repos = _build_repositories(bq_client, config)
    gcs_client = GCSClient(config.gcp.gcs_bucket, config.gcp.project_id)

    dag_run_id = args.run_id or (
        f"manual__{args.date}"
        f"T{datetime.now(timezone.utc).strftime('%H%M%S')}"
        f"__{uuid.uuid4().hex[:8]}"
    )
    execution_date = args.date

    logger.info("Pipeline config loaded")
    logger.info("Mode: %s | Date: %s | Run ID: %s", args.mode, execution_date, dag_run_id)

    if args.manual_channel_id:
        run_manual_channel(
            config,
            repos,
            gcs_client,
            dag_run_id,
            execution_date,
            args.manual_channel_id,
            args.lookback_days,
            args.crawl_mode,
        )
    elif args.mode == "videos":
        run_videos(config, repos, gcs_client, dag_run_id, execution_date)
    elif args.mode == "comments":
        run_comments(config, repos, gcs_client, dag_run_id)
    else:
        run_full(config, repos, gcs_client, dag_run_id, execution_date)

    logger.info("Pipeline finished")


if __name__ == "__main__":
    main()
