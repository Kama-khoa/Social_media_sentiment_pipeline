from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dotenv import load_dotenv
from google.cloud import bigquery

from elt.config import load_config
from elt.datacontext.gcs_client import GCSClient
from elt.extract.helpers.youtube_api_client import YouTubeApiClient
from elt.extract.helpers.ytdlp_video_fetcher import YtdlpVideoFetcher
from elt.extract.comment_extractor import CommentExtractor
from elt.repositories.crawl_state_repository import CrawlStateRepository
from elt.repositories.quota_repository import QuotaRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(project_root / "logs" / "product_crawl.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("run_product_crawl")

def update_task_status(task_id: str, status: str, progress: int, message: str, error: str | None = None) -> None:
    task_dir = project_root / "data" / "crawl_tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.json"
    
    payload = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "error": error,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Task %s progress: %d%% - %s", task_id, progress, message)

def run_cmd(args: list[str]) -> subprocess.CompletedProcess:
    import subprocess
    logger.info("Executing subcommand: %s", " ".join(args))
    return subprocess.run(args, cwd=str(project_root), capture_output=True, text=True, encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Background orchestrator script for single product crawl pipeline.")
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--method", choices=["api", "ytdlp"], default="api")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--max-comments", type=int, default=50)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()

    task_id = args.task_id
    product_id = args.product_id
    keyword = args.keyword
    method = args.method
    max_results = args.max_results
    max_comments = args.max_comments

    try:
        load_dotenv()
        config = load_config()

        project_id = config.gcp.project_id
        dataset = config.gcp.dataset
        bucket_name = config.gcp.gcs_bucket

        # -------------------------------------------------------------
        # STEP 1: Search & Save Videos (0% -> 20%)
        # -------------------------------------------------------------
        update_task_status(task_id, "running", 10, f"Đang tìm kiếm video với từ khóa '{keyword}' ({method.upper()})...")
        
        bq_client = bigquery.Client(project=project_id)
        crawl_state_repo = CrawlStateRepository(bq_client, project_id, dataset)
        quota_repo = QuotaRepository(bq_client, project_id, dataset)
        gcs_client = GCSClient(bucket_name, project_id)

        video_dtos = []
        units_used = 0

        if method == "api":
            api_client = YouTubeApiClient(config.youtube_api_key)
            raw_results = api_client.search_by_keyword(keyword, max_results=max_results)
            units_used += 100
            
            if raw_results:
                video_ids = [item["id"] for item in raw_results]
                video_dtos = api_client.get_video_details(video_ids)
                units_used += (len(video_ids) + 49) // 50
        else:
            # yt-dlp search fallback
            # Construct ytdlp video fetcher keywords config format
            from elt.datacontext.models.keyword_dto import KeywordDTO
            kw_dto = KeywordDTO(keyword_id="tmp", keyword_text=keyword, search_cluster="_uncategorized", is_active=True)
            fetcher = YtdlpVideoFetcher(
                keywords=[kw_dto],
                max_workers=config.crawl.enrich_max_workers,
                cookies_paths=config.crawl.ytdlp_cookies_paths,
                session_cooldown_seconds=config.crawl.ytdlp_session_cooldown_seconds,
            )
            raw_results = fetcher.search_by_keyword(keyword, max_results=max_results)
            
            if raw_results:
                enriched = fetcher.enrich_batch(raw_results)
                video_dtos = fetcher.build_video_dtos(enriched, channel_id="", search_mode="KEYWORD_SEARCH")

        # Map to keyword config so that dbt maps properly
        for dto in video_dtos:
            dto.keyword_matched = keyword
            dto.search_mode = "KEYWORD_SEARCH"

        logger.info("Found %d video dtos", len(video_dtos))

        # Log quota usage for video search if API was used
        if method == "api" and units_used > 0:
            quota_repo.log_operation(
                operation_type="video_extraction_keyword_manual",
                bucket="youtube_search",
                units_used=units_used,
                dag_run_id=task_id,
                videos_processed=len(video_dtos),
                execution_time_seconds=0.0
            )

        if not video_dtos:
            update_task_status(task_id, "success", 100, "Không tìm thấy video mới nào liên quan.")
            return

        # Upload to GCS (GCS-first)
        now = datetime.now(timezone.utc)
        gcs_path = GCSClient.build_videos_path(now)
        payload = [v.to_dict() for v in video_dtos]
        gcs_client.upload_json(gcs_path, payload)

        # Save to BigQuery Crawl State (BQ-second)
        crawl_state_repo.bulk_upsert_from_video_dtos(video_dtos)

        # -------------------------------------------------------------
        # STEP 2: Scrape Comments (20% -> 40%)
        # -------------------------------------------------------------
        update_task_status(task_id, "running", 30, f"Đang thu thập bình luận cho {len(video_dtos)} videos...")
        
        # Override comment worker configurations dynamically to limit limits & age days check
        proxy_config = None
        if config.brightdata_proxy_host:
            from elt.extract.helpers.comment_downloader import ProxyConfig
            proxy_config = ProxyConfig(
                host=config.brightdata_proxy_host,
                port=int(config.brightdata_proxy_port),
                username=config.brightdata_username,
                password=config.brightdata_password
            )
        
        comment_extractor = CommentExtractor(
            config=config,
            crawl_state_repo=crawl_state_repo,
            quota_repo=quota_repo,
            gcs_client=gcs_client,
            proxy_config=proxy_config,
        )
        
        # Override settings for fast manual product crawl run
        comment_extractor._worker._max_comments = max_comments
        comment_extractor._worker._min_age_days = 0 # crawl immediately even if new
        
        comment_extractor.crawl_batch_with_retry(video_dtos, max_retries=1)

        # -------------------------------------------------------------
        # STEP 3: Chạy dbt staging (40% -> 60%)
        # -------------------------------------------------------------
        update_task_status(task_id, "running", 50, "Đang xử lý dbt transform (staging)...")
        
        # Call dbt staging
        dbt_stg = run_cmd([sys.executable, "scripts/dbt/dbt_runner.py", "run", "--select", "stg_youtube_videos stg_youtube_comments int_comment_sentences"])
        if dbt_stg.returncode != 0:
            logger.error("dbt staging failed: %s", dbt_stg.stderr)
            raise RuntimeError(f"dbt transform (staging) thất bại: {dbt_stg.stderr or dbt_stg.stdout}")

        # -------------------------------------------------------------
        # STEP 4: Chạy NLP analysis (60% -> 80%)
        # -------------------------------------------------------------
        update_task_status(task_id, "running", 70, "Đang chạy mô hình NLP phân tích khía cạnh & cảm xúc...")
        
        nlp_run = run_cmd([sys.executable, "-m", "nlp.runner", "--product-id", product_id, "--limit", "2000", "--reprocess", "--dag-run-id", task_id])
        if nlp_run.returncode != 0:
            logger.error("nlp runner failed: %s", nlp_run.stderr)
            raise RuntimeError(f"Phân tích NLP thất bại: {nlp_run.stderr or nlp_run.stdout}")

        # -------------------------------------------------------------
        # STEP 5: Chạy dbt marts & resolver (80% -> 100%)
        # -------------------------------------------------------------
        update_task_status(task_id, "running", 90, "Đang đồng bộ dữ liệu lên bảng xếp hạng và báo cáo...")
        
        # Call dbt marts
        dbt_marts = run_cmd([sys.executable, "scripts/dbt/dbt_runner.py", "run", "--select", "int_sentiment_results int_video_product_mentions int_sentence_product_targets fact_product_mentions agg_daily_product_ranking"])
        if dbt_marts.returncode != 0:
            logger.error("dbt marts failed: %s", dbt_marts.stderr)
            raise RuntimeError(f"dbt transform (marts) thất bại: {dbt_marts.stderr or dbt_marts.stdout}")

        # Call product resolver
        resolver_run = run_cmd([sys.executable, "-m", "nlp.product_target_resolver", "--limit", "100"])
        if resolver_run.returncode != 0:
            logger.warning("Product target resolver failed: %s", resolver_run.stderr)

        # Log daily quota summary checkpoint
        quota_repo.upsert_daily_summary(now.date(), task_id)
        
        # Complete
        update_task_status(task_id, "success", 100, "Hoàn thành thu thập và phân tích dữ liệu cho sản phẩm thành công!")
        
    except Exception as e:
        err_msg = str(e)
        logger.error("Crawl pipeline error: %s", err_msg)
        logger.error(traceback.format_exc())
        update_task_status(task_id, "failed", 100, f"Lỗi tiến trình: {err_msg}", error=traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
