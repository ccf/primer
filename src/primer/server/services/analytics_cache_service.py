from __future__ import annotations

import json
import time
from datetime import date, datetime
from hashlib import sha256
from typing import Any

from primer.common.config import settings
from primer.server.services.observability_service import record_counter

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - local/dev fallback when redis isn't installed
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass


_redis_client: Redis | None = None
_redis_disabled_until: float | None = None


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

    global _redis_client, _redis_disabled_until
    if _redis_disabled_until is not None:
        if time.monotonic() < _redis_disabled_until:
            return None
        _redis_disabled_until = None
        _redis_client = None
    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
        except Exception:
            _disable_cache_client()
            return None
    return _redis_client


def _build_cache_key(namespace: str, params: dict[str, Any]) -> str:
    normalized = json.dumps(_normalize_cache_value(params), sort_keys=True, separators=(",", ":"))
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    return f"primer:analytics:{namespace}:{digest}"


def _disable_cache_client() -> None:
    global _redis_client, _redis_disabled_until
    _redis_client = None
    _redis_disabled_until = time.monotonic() + settings.analytics_cache_error_backoff_seconds


def get_cached_json(namespace: str, params: dict[str, Any]) -> Any | None:
    client = _get_redis_client()
    if client is None:
        record_counter(
            "primer.analytics_cache.requests",
            1,
            {"namespace": namespace, "result": "disabled"},
        )
        return None
    try:
        payload = client.get(_build_cache_key(namespace, params))
    except (RedisError, OSError):
        _disable_cache_client()
        record_counter(
            "primer.analytics_cache.requests",
            1,
            {"namespace": namespace, "result": "error"},
        )
        return None
    if not payload:
        record_counter(
            "primer.analytics_cache.requests",
            1,
            {"namespace": namespace, "result": "miss"},
        )
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        record_counter(
            "primer.analytics_cache.requests",
            1,
            {"namespace": namespace, "result": "decode_error"},
        )
        return None
    record_counter(
        "primer.analytics_cache.requests",
        1,
        {"namespace": namespace, "result": "hit"},
    )
    return decoded


def set_cached_json(
    namespace: str,
    params: dict[str, Any],
    payload: Any,
    *,
    ttl_seconds: int | None = None,
) -> None:
    client = _get_redis_client()
    if client is None:
        record_counter(
            "primer.analytics_cache.writes",
            1,
            {"namespace": namespace, "result": "disabled"},
        )
        return
    try:
        client.setex(
            _build_cache_key(namespace, params),
            ttl_seconds or settings.analytics_cache_ttl_seconds,
            json.dumps(payload, separators=(",", ":")),
        )
        record_counter(
            "primer.analytics_cache.writes",
            1,
            {"namespace": namespace, "result": "success"},
        )
    except (RedisError, OSError):
        _disable_cache_client()
        record_counter(
            "primer.analytics_cache.writes",
            1,
            {"namespace": namespace, "result": "error"},
        )
        return
    except (TypeError, ValueError):
        record_counter(
            "primer.analytics_cache.writes",
            1,
            {"namespace": namespace, "result": "serialize_error"},
        )
        return
