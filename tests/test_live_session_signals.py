from datetime import UTC, datetime
from types import SimpleNamespace

from primer.hook.extractor import SessionMetadata
from primer.mcp.reader import LocalSession
from primer.server.services.live_session_signal_service import get_live_session_signals


def test_live_session_signals_selects_latest_session(monkeypatch, tmp_path):
    older_path = tmp_path / "older.jsonl"
    newer_path = tmp_path / "newer.jsonl"
    older_path.write_text("{}\n")
    newer_path.write_text("{}\n")
    older_path.touch()
    newer_path.touch()

    sessions = [
        LocalSession(
            session_id="old-session",
            transcript_path=str(older_path),
            facets_path=None,
            has_facets=False,
            project_path="/repo/old-project",
            agent_type="claude_code",
        ),
        LocalSession(
            session_id="new-session",
            transcript_path=str(newer_path),
            facets_path=None,
            has_facets=False,
            project_path="/repo/new-project",
            agent_type="claude_code",
        ),
    ]
    monkeypatch.setattr(
        "primer.server.services.live_session_signal_service.list_local_sessions",
        lambda: sessions,
    )

    now = datetime.now(tz=UTC)

    def fake_extract(path: str) -> SessionMetadata:
        if path == str(newer_path):
            return SessionMetadata(
                session_id="new-session",
                project_name="new-project",
                agent_type="claude_code",
                started_at=now,
                messages=[
                    {"ordinal": 0, "role": "human", "content_text": "Debug the auth regression"},
                    {
                        "ordinal": 1,
                        "role": "assistant",
                        "tool_calls": [
                            {"name": "Bash", "input_preview": "pytest tests/test_auth.py"}
                        ],
                    },
                    {
                        "ordinal": 2,
                        "role": "tool_result",
                        "tool_results": [{"name": "Bash", "output_preview": "2 failed, 10 passed"}],
                    },
                    {"ordinal": 3, "role": "human", "content_text": "Still broken, try again"},
                    {
                        "ordinal": 4,
                        "role": "assistant",
                        "tool_calls": [{"name": "Read", "input_preview": '{"path":"auth.py"}'}],
                    },
                    {
                        "ordinal": 5,
                        "role": "assistant",
                        "tool_calls": [{"name": "Edit", "input_preview": '{"path":"auth.py"}'}],
                    },
                    {
                        "ordinal": 6,
                        "role": "assistant",
                        "tool_calls": [
                            {"name": "Bash", "input_preview": "pytest tests/test_auth.py"}
                        ],
                    },
                    {
                        "ordinal": 7,
                        "role": "tool_result",
                        "tool_results": [{"name": "Bash", "output_preview": "1 failed"}],
                    },
                    {
                        "ordinal": 8,
                        "role": "assistant",
                        "tool_calls": [{"name": "github_search", "input_preview": "{}"}],
                    },
                    {
                        "ordinal": 9,
                        "role": "tool_result",
                        "tool_results": [
                            {
                                "name": "github_search",
                                "output_preview": "Tool error: timeout",
                            }
                        ],
                    },
                    {
                        "ordinal": 10,
                        "role": "assistant",
                        "tool_calls": [{"name": "jira_lookup", "input_preview": "{}"}],
                    },
                    {
                        "ordinal": 11,
                        "role": "tool_result",
                        "tool_results": [
                            {
                                "name": "jira_lookup",
                                "output_preview": "Request failed with exception",
                            }
                        ],
                    },
                ],
            )
        return SessionMetadata(
            session_id="old-session",
            project_name="old-project",
            agent_type="claude_code",
            started_at=now,
            messages=[
                {"ordinal": 0, "role": "human", "content_text": "Great, that fixed it. Thanks!"}
            ],
        )

    monkeypatch.setattr(
        "primer.server.services.live_session_signal_service.get_extractor_for",
        lambda _agent_type: SimpleNamespace(extract=fake_extract),
    )

    response = get_live_session_signals()

    assert response.session_id == "new-session"
    assert response.project_name == "new-project"
    assert response.risk_level == "high"
    assert response.satisfaction_signal == "negative"
    signal_titles = {signal.title for signal in response.signals}
    assert "Verification is failing" in signal_titles
    assert "Tool errors are stacking up" in signal_titles
    assert "Recovery loop detected" in signal_titles
    assert "User sentiment looks frustrated" in signal_titles


def test_live_session_signals_support_explicit_session_lookup(monkeypatch, tmp_path):
    transcript_path = tmp_path / "healthy.jsonl"
    transcript_path.write_text("{}\n")

    monkeypatch.setattr(
        "primer.server.services.live_session_signal_service.list_local_sessions",
        lambda: [
            LocalSession(
                session_id="healthy-session",
                transcript_path=str(transcript_path),
                facets_path=None,
                has_facets=False,
                project_path="/repo/healthy-project",
                agent_type="claude_code",
            )
        ],
    )
    monkeypatch.setattr(
        "primer.server.services.live_session_signal_service.get_extractor_for",
        lambda _agent_type: SimpleNamespace(
            extract=lambda _path: SessionMetadata(
                session_id="healthy-session",
                project_name="healthy-project",
                agent_type="claude_code",
                started_at=datetime.now(tz=UTC),
                messages=[
                    {"ordinal": 0, "role": "human", "content_text": "Run the auth tests"},
                    {
                        "ordinal": 1,
                        "role": "assistant",
                        "tool_calls": [
                            {"name": "Bash", "input_preview": "pytest tests/test_auth.py"}
                        ],
                    },
                    {
                        "ordinal": 2,
                        "role": "tool_result",
                        "tool_results": [
                            {"name": "Bash", "output_preview": "5 passed, 0 failed, 0 errors"}
                        ],
                    },
                    {
                        "ordinal": 3,
                        "role": "human",
                        "content_text": "Great, that fixed it. Thanks!",
                    },
                ],
            )
        ),
    )

    response = get_live_session_signals(session_id="healthy-session")

    assert response.risk_level == "low"
    assert response.satisfaction_signal == "positive"
    assert response.signals[0].title == "Session looks healthy"
