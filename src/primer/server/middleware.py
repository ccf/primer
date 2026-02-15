from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from primer.common.config import settings


def _key_func(request: Request) -> str:
    """Rate-limit key: API key prefix if present, else client IP."""
    api_key = request.headers.get("x-api-key") or ""
    if api_key:
        return api_key[:16]
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=_key_func,
    enabled=settings.rate_limit_enabled,
    default_limits=[settings.rate_limit_default],
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )
