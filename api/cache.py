import json
import logging
from typing import Any

import redis

from api.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    settings = get_settings()
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — caching disabled", exc)
        return None


def get_cached(key: str) -> Any | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.warning("Redis get failed for key %s: %s", key, exc)
        return None


def set_cached(key: str, data: Any, ttl: int = 300) -> None:
    client = _get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(data, default=str))
    except Exception as exc:
        logger.warning("Redis set failed for key %s: %s", key, exc)


def invalidate_prefix(prefix: str) -> None:
    client = _get_redis()
    if client is None:
        return
    try:
        keys = client.keys(f"{prefix}*")
        if keys:
            client.delete(*keys)
    except Exception as exc:
        logger.warning("Redis invalidate failed for prefix %s: %s", prefix, exc)
