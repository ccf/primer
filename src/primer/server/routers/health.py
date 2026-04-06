from fastapi import APIRouter

from primer.common.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/api/v1/demo-config")
def demo_config():
    """Return demo mode configuration for the frontend.

    In demo mode, the admin_key is intentionally exposed so the frontend
    can auto-inject it for unauthenticated visitors. This key only grants
    read access since the DemoReadOnlyMiddleware blocks all mutations.
    """
    if not settings.demo_mode:
        return {"demo_mode": False}

    return {
        "demo_mode": True,
        "admin_key": settings.admin_api_key,
        "read_only": True,
    }
