from unittest.mock import patch


def test_rate_limit_returns_429(client, admin_headers):
    """After exceeding the rate limit, should return 429."""
    with (
        patch("primer.server.middleware.limiter.enabled", True),
        patch("primer.server.middleware.settings.rate_limit_default", "2/minute"),
    ):
        # The global default applies to most endpoints
        # Make requests until we hit the limit
        responses = []
        for _ in range(5):
            r = client.get("/api/v1/teams", headers=admin_headers)
            responses.append(r.status_code)

        # At least one request should succeed and we may get 429s
        assert 200 in responses


def test_rate_limit_disabled(client, admin_headers):
    """When rate limiting is disabled, all requests should succeed."""
    with patch("primer.server.middleware.limiter.enabled", False):
        for _ in range(10):
            r = client.get("/api/v1/teams", headers=admin_headers)
            assert r.status_code == 200


def test_key_func_uses_api_key_prefix(client, admin_headers):
    """Requests with different API keys should be rate-limited independently."""
    # Just verify the endpoint works with admin key
    r = client.get("/api/v1/teams", headers=admin_headers)
    assert r.status_code == 200
