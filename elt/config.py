import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GCPConfig:
    project_id: str
    dataset: str
    gcs_bucket: str
    credentials_path: str


@dataclass
class CrawlConfig:
    max_comments_per_video: int
    historical_scan_channels_per_day: int
    historical_scan_max_results: int
    historical_scan_lookback_days: int
    daily_scan_lookback_days: int
    daily_scan_max_results: int
    enrich_max_workers: int
    video_batch_size: int
    new_video_min_age_days: int
    growing_video_max_age_days: int
    mature_video_max_age_days: int
    growing_recrawl_interval_days: int
    mature_recrawl_interval_days: int
    archived_recrawl_interval_days: int
    ytdlp_cookies_path: str | None
    ytdlp_cookies_paths: list[str]
    ytdlp_session_cooldown_seconds: int


@dataclass
class CommentDownloaderConfig:
    request_delay_seconds: float
    max_retries: int


@dataclass
class QuotaConfig:
    daily_budget: int
    safety_buffer: int
    bucket_search: int
    bucket_channel_seed: int


@dataclass
class PipelineConfig:
    gcp: GCPConfig
    crawl: CrawlConfig
    comment_downloader: CommentDownloaderConfig
    quota: QuotaConfig
    youtube_api_key: str
    gemini_api_key: str
    brightdata_proxy_host: str
    brightdata_proxy_port: str
    brightdata_username: str
    brightdata_password: str


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def load_config(config_path: str | None = None) -> PipelineConfig:
    resolved: Path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).parent.parent / "config" / "pipeline_config.yaml"
    )

    with open(resolved, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    crawl = raw["crawl"]
    downloader = raw["comment_downloader"]
    quota = raw["quota"]

    return PipelineConfig(
        gcp=GCPConfig(
            project_id=_require_env("GCP_PROJECT_ID"),
            dataset=_require_env("BQ_DATASET"),
            gcs_bucket=_require_env("GCS_BUCKET_NAME"),
            credentials_path=_require_env("GOOGLE_APPLICATION_CREDENTIALS"),
        ),
        crawl=CrawlConfig(
            max_comments_per_video=crawl["max_comments_per_video"],
            historical_scan_channels_per_day=crawl["historical_scan_channels_per_day"],
            historical_scan_max_results=crawl["historical_scan_max_results"],
            historical_scan_lookback_days=crawl.get("historical_scan_lookback_days", 730),
            daily_scan_lookback_days=crawl["daily_scan_lookback_days"],
            daily_scan_max_results=crawl["daily_scan_max_results"],
            enrich_max_workers=crawl["enrich_max_workers"],
            video_batch_size=crawl["video_batch_size"],
            new_video_min_age_days=crawl["new_video_min_age_days"],
            growing_video_max_age_days=crawl["growing_video_max_age_days"],
            mature_video_max_age_days=crawl["mature_video_max_age_days"],
            growing_recrawl_interval_days=crawl["growing_recrawl_interval_days"],
            mature_recrawl_interval_days=crawl["mature_recrawl_interval_days"],
            archived_recrawl_interval_days=crawl["archived_recrawl_interval_days"],
            ytdlp_cookies_path=crawl.get("ytdlp_cookies_path"),
            ytdlp_cookies_paths=crawl.get("ytdlp_cookies_paths") or (
                [crawl["ytdlp_cookies_path"]]
                if crawl.get("ytdlp_cookies_path")
                else []
            ),
            ytdlp_session_cooldown_seconds=crawl.get(
                "ytdlp_session_cooldown_seconds",
                3600,
            ),
        ),
        comment_downloader=CommentDownloaderConfig(
            request_delay_seconds=downloader["request_delay_seconds"],
            max_retries=downloader["max_retries"],
        ),
        quota=QuotaConfig(
            daily_budget=quota["daily_budget"],
            safety_buffer=quota["safety_buffer"],
            bucket_search=quota["bucket_search"],
            bucket_channel_seed=quota["bucket_channel_seed"],
        ),
        youtube_api_key=_require_env("YOUTUBE_API_KEY"),
        gemini_api_key=_require_env("GEMINI_API_KEY"),
        brightdata_proxy_host=_require_env("BRIGHTDATA_PROXY_HOST"),
        brightdata_proxy_port=_require_env("BRIGHTDATA_PROXY_PORT"),
        brightdata_username=_require_env("BRIGHTDATA_USERNAME"),
        brightdata_password=_require_env("BRIGHTDATA_PASSWORD"),
    )
