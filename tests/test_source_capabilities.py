from primer.common.schemas import SessionIngestPayload
from primer.common.source_capabilities import AgentCapability, get_capability_for


def test_cursor_capability_exists():
    cap = get_capability_for("cursor")

    assert cap == AgentCapability(
        agent_type="cursor",
        transcript="required",
        tool_calls="optional",
        model_usage="optional",
        facets="optional",
        native_discovery="required",
    )
    assert cap.supports_transcript is True
    assert cap.supports_tool_calls is True
    assert cap.supports_model_usage is True
    assert cap.supports_facets is True
    assert cap.parity_for("transcript") == "required"
    assert cap.parity_for("tool_calls") == "optional"


def test_codex_gemini_and_cursor_support_transcript_derived_facets():
    codex = get_capability_for("codex_cli")
    gemini = get_capability_for("gemini_cli")
    cursor = get_capability_for("cursor")

    assert codex is not None
    assert gemini is not None
    assert cursor is not None
    assert codex.facets == "optional"
    assert gemini.facets == "optional"
    assert cursor.facets == "optional"
    assert codex.supports_facets is True
    assert gemini.supports_facets is True
    assert cursor.supports_facets is True


def test_unknown_agent_capability_is_none():
    assert get_capability_for("totally_unknown") is None


def test_session_ingest_payload_accepts_cursor_agent_type():
    payload = SessionIngestPayload(
        session_id="cursor-session-1",
        api_key="test-key",
        agent_type="cursor",
    )

    assert payload.agent_type == "cursor"
