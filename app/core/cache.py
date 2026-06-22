"""Tiny cache with Redis backend and a graceful in-memory fallback.

If Redis is unreachable (or disabled), it transparently uses a process-local
dict, so the app and tests work without a running Redis.
"""
import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self) -> None:
        self._redis = None
        self._mem: dict[str, Any] = {}
        self._checked = False

    def _client(self):
        if self._checked:
            return self._redis
        self._checked = True
        if settings.cache_enabled:
            try:
                import redis

                client = redis.Redis.from_url(
                    settings.redis_url, socket_connect_timeout=0.3, decode_responses=True
                )
                client.ping()
                self._redis = client
                logger.info("Cache: using Redis at %s", settings.redis_url)
            except Exception:  # noqa: BLE001
                logger.info("Cache: Redis unavailable, using in-memory fallback")
                self._redis = None
        return self._redis

    def get(self, key: str) -> Any | None:
        if not settings.cache_enabled:
            return None
        client = self._client()
        if client is not None:
            try:
                raw = client.get(key)
                return json.loads(raw) if raw is not None else None
            except Exception:  # noqa: BLE001
                logger.warning("Cache get failed", exc_info=True)
        return self._mem.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not settings.cache_enabled:
            return
        ttl = ttl or settings.cache_ttl_seconds
        client = self._client()
        if client is not None:
            try:
                client.set(key, json.dumps(value), ex=ttl)
                return
            except Exception:  # noqa: BLE001
                logger.warning("Cache set failed", exc_info=True)
        self._mem[key] = value


cache = Cache()
