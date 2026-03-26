from primer.common.schemas import (
    CoachingBrief,
    CoachingSection,
    InSessionNudgesResponse,
    LiveSessionSignal,
    LiveSessionSignalsResponse,
)
from primer.mcp.nudges import build_in_session_nudges


def test_build_in_session_nudges_maps_live_risks_to_actions():
    live_signals = LiveSessionSignalsResponse(
        session_id="session-123",
        agent_type="claude_code",
        project_name="api-server",
        total_messages=18,
        risk_level="high",
        satisfaction_signal="negative",
        signals=[
            LiveSessionSignal(
                signal_type="verification_failure",
                severity="warning",
                title="Verification is failing",
                detail="Recent test runs are failing repeatedly.",
            ),
            LiveSessionSignal(
                signal_type="recovery_loop",
                severity="critical",
                title="Recovery loop detected",
                detail="The session is repeating the same recovery pattern.",
            ),
        ],
    )
    coaching_brief = CoachingBrief(
        status_summary="Session-start brief",
        brief_type="session_start",
        sections=[
            CoachingSection(
                title="How to start this session",
                items=["**Debugging: Read -> Test -> Fix** — Start with Read, Bash."],
            ),
            CoachingSection(
                title="What to reach for",
                items=["**Model choice** — Use Sonnet for debugging work."],
            ),
            CoachingSection(
                title="What to watch for",
                items=["**Watch for tool_error** — it shows up often on this project."],
            ),
        ],
        sessions_analyzed=12,
        generated_at="2026-03-26T12:00:00Z",
    )

    result = build_in_session_nudges(live_signals, coaching_brief)

    assert isinstance(result, InSessionNudgesResponse)
    assert result.risk_level == "high"
    assert result.nudges[0].nudge_type == "break_recovery_loop"
    assert result.nudges[0].severity == "critical"
    assert any(
        "Debugging: Read -> Test -> Fix" in action for action in result.nudges[0].suggested_actions
    )
    assert any(nudge.nudge_type == "tighten_verification_loop" for nudge in result.nudges)


def test_build_in_session_nudges_returns_stay_the_course_for_healthy_sessions():
    live_signals = LiveSessionSignalsResponse(
        session_id="session-healthy",
        agent_type="claude_code",
        total_messages=4,
        risk_level="low",
        satisfaction_signal="positive",
        signals=[
            LiveSessionSignal(
                signal_type="positive_momentum",
                severity="info",
                title="Session looks healthy",
                detail="Recent interaction signals look positive and unblocked.",
            )
        ],
    )

    result = build_in_session_nudges(live_signals, None)

    assert result.risk_level == "low"
    assert result.nudges[0].title in {"Keep the loop tight", "Stay on the current path"}
