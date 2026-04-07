"""Read-only middleware for the public demo instance.

When PRIMER_DEMO_MODE=true, all mutating requests (POST, PUT, PATCH, DELETE)
are blocked with a friendly 403 response. A small whitelist of safe POST
endpoints is allowed (e.g. explorer chat which is read-only semantically).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# POST endpoints that are semantically read-only (no mutations).
# Note: explorer chat is intentionally NOT whitelisted; it's blocked with
# 403 in the router itself in demo mode to prevent abuse of the LLM API.
_SAFE_POST_PATHS: set[str] = {
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}

# Prefixes for safe POST paths. Empty by default — add only paths whose
# entire subtree is provably mutation-free.
_SAFE_POST_PREFIXES: tuple[str, ...] = ()

_BLOCKED_BODY = {"detail": "This is a read-only demo instance. Mutations are disabled."}


def _blocked_response() -> JSONResponse:
    """Fresh response per request — Response objects carry mutable state."""
    return JSONResponse(_BLOCKED_BODY, status_code=403)


class DemoReadOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            path = request.url.path

            # Whitelist only applies to POST — we never allow PUT/PATCH/DELETE
            if method == "POST":
                if path in _SAFE_POST_PATHS:
                    return await call_next(request)

                for prefix in _SAFE_POST_PREFIXES:
                    if path.startswith(prefix):
                        return await call_next(request)

            return _blocked_response()

        return await call_next(request)
