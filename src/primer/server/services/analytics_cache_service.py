from __future__ import annotations

import json
from datetime import date, datetime
from hashlib import sha256
from typing import Any

from primer.common.config import settings

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - local/dev fallback when redis isn't installed
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass


_redis_client: Redis | bool | None = None


def _normalize_cache_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_cache_value(val) for key, val in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_cache_value(item) for item in value]
    return value


def _get_redis_client() -> Redis | None:
    if not settings.analytics_cache_enabled or not settings.redis_url or Redis is None:
        return None

    global _redis_client
    if _redis_client is False:
        return None
    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
        except Exception:
            _redis_client = False
            return None
    return _redis_client


def _build_cache_key(namespace: str, params: dict[str, Any]) -> str:
    normalized = json.dumps(_normalize_cache_value(params), sort_keys=True, separators=(",", ":"))
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    return f"primer:analytics:{namespace}:{digest}"


def _disable_cache_client() -> None:
    global _redis_client
    _redis_client = False


def get_cached_json(namespace: str, params: dict[str, Any]) -> Any | None:
    client = _get_redis_client()
    if client is None:
        return None
    try:
        payload = client.get(_build_cache_key(namespace, params))
    except (RedisError, OSError):
        _disable_cache_client()
        return None
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def set_cached_json(
    namespace: str,
    params: dict[str, Any],
    payload: Any,
    *,
    ttl_seconds: int | None = None,
) -> None:
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.setex(
            _build_cache_key(namespace, params),
            ttl_seconds or settings.analytics_cache_ttl_seconds,
            json.dumps(payload, separators=(",", ":")),
        )
    except (RedisError, OSError):
        _disable_cache_client()
        return
    except (TypeError, ValueError):
        return
