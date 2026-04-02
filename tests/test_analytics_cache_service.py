from primer.server.services import analytics_cache_service


def test_get_cached_json_returns_none_without_redis_url(monkeypatch):
    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "")
    analytics_cache_service._redis_client = None

    assert analytics_cache_service.get_cached_json("overview", {"team_id": None}) is None


def test_set_cached_json_noops_without_redis_url(monkeypatch):
    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "")
    analytics_cache_service._redis_client = None

    analytics_cache_service.set_cached_json("overview", {"team_id": None}, {"total_sessions": 1})


def test_get_cached_json_disables_cache_after_redis_error(monkeypatch):
    class BrokenRedis:
        def get(self, _key):
            raise OSError("boom")

    monkeypatch.setattr(analytics_cache_service, "Redis", object)
    analytics_cache_service._redis_client = BrokenRedis()
    monkeypatch.setattr(analytics_cache_service.settings, "analytics_cache_enabled", True)
    monkeypatch.setattr(analytics_cache_service.settings, "redis_url", "redis://localhost:6379/0")

    assert analytics_cache_service.get_cached_json("overview", {"team_id": None}) is None
    assert analytics_cache_service._redis_client is False
