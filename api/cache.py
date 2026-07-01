import json
import logging
import time
from typing import Any

import redis

from api.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_redis_down_until = 0.0
_REDIS_RETRY_COOLDOWN_SECONDS = 30.0


def _get_redis() -> redis.Redis | None:
    global _redis_client, _redis_down_until
    settings = get_settings()
    if not settings.cache_enabled:
        return None
    if _redis_client is not None:
        return _redis_client
    if time.monotonic() < _redis_down_until:
        return None
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.5,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        _redis_down_until = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS
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
        global _redis_client, _redis_down_until
        _redis_client = None
        _redis_down_until = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS
        logger.warning("Redis get failed for key %s: %s", key, exc)
        return None


def set_cached(key: str, data: Any, ttl: int = 300) -> None:
    client = _get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(data, default=str))
    except Exception as exc:
        global _redis_client, _redis_down_until
        _redis_client = None
        _redis_down_until = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS
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
        global _redis_client, _redis_down_until
        _redis_client = None
        _redis_down_until = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS
        logger.warning("Redis invalidate failed for prefix %s: %s", prefix, exc)
