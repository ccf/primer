"""Read-only middleware for the public demo instance.

When PRIMER_DEMO_MODE=true, all mutating requests (POST, PUT, PATCH, DELETE)
are blocked with a friendly 403 response. A small whitelist of safe POST
endpoints is allowed (e.g. explorer chat which is read-only semantically).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# POST endpoints that are semantically read-only (no mutations)
_SAFE_POST_PATHS: set[str] = {
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}

# Prefixes for safe POST paths (e.g. explorer chat uses SSE streaming)
_SAFE_POST_PREFIXES: tuple[str, ...] = ("/api/v1/explorer/",)

_BLOCKED_RESPONSE = JSONResponse(
    {"detail": "This is a read-only demo instance. Mutations are disabled."},
    status_code=403,
)


class DemoReadOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            path = request.url.path

            # Allow whitelisted safe endpoints
            if path in _SAFE_POST_PATHS:
                return await call_next(request)

            for prefix in _SAFE_POST_PREFIXES:
                if path.startswith(prefix):
                    return await call_next(request)

            return _BLOCKED_RESPONSE

        return await call_next(request)
