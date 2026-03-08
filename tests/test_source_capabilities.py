from primer.common.schemas import SessionIngestPayload
from primer.common.source_capabilities import AgentCapability, get_capability_for


def test_cursor_capability_exists():
    cap = get_capability_for("cursor")

    assert cap == AgentCapability(
        agent_type="cursor",
        supports_transcript=True,
        supports_tool_calls=False,
        supports_model_usage=False,
        supports_facets=False,
        supports_native_discovery=False,
    )


def test_unknown_agent_capability_is_none():
    assert get_capability_for("totally_unknown") is None


def test_session_ingest_payload_accepts_cursor_agent_type():
    payload = SessionIngestPayload(
        session_id="cursor-session-1",
        api_key="test-key",
        agent_type="cursor",
    )

    assert payload.agent_type == "cursor"
