from primer.common.schemas import SessionIngestPayload
from primer.common.source_capabilities import AgentCapability, get_capability_for


def test_cursor_capability_exists():
    cap = get_capability_for("cursor")

    assert cap == AgentCapability(
        agent_type="cursor",
        transcript="required",
        tool_calls="unavailable",
        model_usage="unavailable",
        facets="unavailable",
        native_discovery="unavailable",
    )
    assert cap.supports_transcript is True
    assert cap.supports_tool_calls is False
    assert cap.parity_for("transcript") == "required"
    assert cap.parity_for("tool_calls") == "unavailable"


def test_unknown_agent_capability_is_none():
    assert get_capability_for("totally_unknown") is None


def test_session_ingest_payload_accepts_cursor_agent_type():
    payload = SessionIngestPayload(
        session_id="cursor-session-1",
        api_key="test-key",
        agent_type="cursor",
    )

    assert payload.agent_type == "cursor"
