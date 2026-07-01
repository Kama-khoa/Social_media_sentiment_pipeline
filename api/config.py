import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod-123456")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    app_database_url: str = os.getenv("APP_DATABASE_URL") or os.getenv("POSTGRES_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/sentiment_webapi")
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() in ("1", "true", "yes", "on")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    airflow_base_url: str = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
    airflow_api_username: str = os.getenv("AIRFLOW_API_USERNAME", "admin")
    airflow_api_password: str = os.getenv("AIRFLOW_API_PASSWORD", "admin")
    next_public_api_base_url: str = os.getenv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000")
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    bq_dataset: str = os.getenv("BQ_DATASET", "sentiment_platform")
    bq_marts_dataset: str = os.getenv("BQ_DATASET", "sentiment_platform") + "_marts"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
