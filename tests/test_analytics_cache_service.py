from primer.server.services import analytics_cache_service


def test_get_cached_json_returns_none_without_redis_url(monkeypatch):
    counters: list[tuple[str, int | float, dict[str, str]]] = []

    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "")
    monkeypatch.setattr(
        analytics_cache_service,
        "record_counter",
        lambda name, value, attributes=None: counters.append((name, value, attributes or {})),
    )
    analytics_cache_service._redis_client = None
    analytics_cache_service._redis_disabled_until = None

    assert analytics_cache_service.get_cached_json("overview", {"team_id": None}) is None
    assert counters == []


def test_set_cached_json_noops_without_redis_url(monkeypatch):
    counters: list[tuple[str, int | float, dict[str, str]]] = []

    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "")
    monkeypatch.setattr(
        analytics_cache_service,
        "record_counter",
        lambda name, value, attributes=None: counters.append((name, value, attributes or {})),
    )
    analytics_cache_service._redis_client = None
    analytics_cache_service._redis_disabled_until = None

    analytics_cache_service.set_cached_json("overview", {"team_id": None}, {"total_sessions": 1})
    assert counters == []


def test_get_cached_json_backs_off_after_redis_error(monkeypatch):
    class BrokenRedis:
        def get(self, _key):
            raise OSError("boom")

    monkeypatch.setattr(analytics_cache_service, "Redis", object)
    monkeypatch.setattr(
        analytics_cache_service.settings,
        "analytics_cache_error_backoff_seconds",
        30,
    )
    analytics_cache_service._redis_client = BrokenRedis()
    analytics_cache_service._redis_disabled_until = None
    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "redis://localhost:6379/0")

    assert analytics_cache_service.get_cached_json("overview", {"team_id": None}) is None
    assert analytics_cache_service._redis_client is None
    assert analytics_cache_service._redis_disabled_until is not None


def test_get_cached_json_records_decode_error_without_hit(monkeypatch):
    counters: list[tuple[str, int | float, dict[str, str]]] = []

    class BrokenPayloadRedis:
        def get(self, _key):
            return "{not-json"

    monkeypatch.setattr(analytics_cache_service, "Redis", object)
    monkeypatch.setattr(
        analytics_cache_service,
        "record_counter",
        lambda name, value, attributes=None: counters.append((name, value, attributes or {})),
    )
    analytics_cache_service._redis_client = BrokenPayloadRedis()
    analytics_cache_service._redis_disabled_until = None
    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "redis://localhost:6379/0")

    assert analytics_cache_service.get_cached_json("overview", {"team_id": None}) is None
    assert counters == [
        (
            "primer.analytics_cache.requests",
            1,
            {"namespace": "overview", "result": "decode_error"},
        )
    ]
