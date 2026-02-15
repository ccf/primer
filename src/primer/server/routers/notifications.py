from fastapi import APIRouter, Depends

from primer.common.config import settings
from primer.server.deps import AuthContext, require_role
from primer.server.services.slack_service import send_test_message

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/slack")
def slack_config(_auth: AuthContext = Depends(require_role("admin"))):
    return {
        "webhook_url_set": bool(settings.slack_webhook_url),
        "enabled": settings.slack_alerts_enabled,
    }


@router.post("/slack/test")
def test_slack(_auth: AuthContext = Depends(require_role("admin"))):
    if not settings.slack_webhook_url:
        return {"success": False, "error": "No webhook URL configured"}
    success, error = send_test_message(settings.slack_webhook_url)
    result: dict = {"success": success}
    if error:
        result["error"] = error
    return result
