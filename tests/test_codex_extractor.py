import json
import tempfile

from primer.hook.codex_extractor import CodexExtractor


def _write_jsonl(lines: list[dict]) -> str:
    """Write JSONL lines to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        for line in lines:
            tmp.write(json.dumps(line) + "\n")
        return tmp.name


def test_extract_empty_file():
    extractor = CodexExtractor()
    path = _write_jsonl([])
    meta = extractor.extract(path)
    assert meta.message_count == 0
    assert meta.agent_type == "codex_cli"


def test_extract_nonexistent_file():
    extractor = CodexExtractor()
    meta = extractor.extract("/nonexistent/path.jsonl")
    assert meta.message_count == 0
    assert meta.agent_type == "codex_cli"


def test_extract_basic_session():
    lines = [
        {
            "timestamp": "2025-02-01T10:00:00Z",
            "SessionMeta": {
                "id": "thread-abc123",
                "cwd": "/home/user/myapp",
                "cli_version": "0.1.0",
                "model": "o4-mini",
            },
        },
        {
            "timestamp": "2025-02-01T10:00:01Z",
            "TurnContext": {"model": "o4-mini", "approval_policy": "auto-edit"},
        },
        {
            "timestamp": "2025-02-01T10:00:02Z",
            "EventMsg": {"type": "UserMessage", "text": "Fix the auth middleware"},
        },
        {
            "timestamp": "2025-02-01T10:00:05Z",
            "EventMsg": {"type": "AgentMessage", "text": "I'll fix the middleware."},
        },
        {
            "timestamp": "2025-02-01T10:00:06Z",
            "EventMsg": {"type": "ExecCommandBegin", "command": "cat auth.py"},
        },
        {
            "timestamp": "2025-02-01T10:00:07Z",
            "ResponseItem": {"type": "function_call", "function_call": {"name": "apply_patch"}},
        },
        {
            "timestamp": "2025-02-01T10:00:08Z",
            "token_count": {
                "model": "o4-mini",
                "input_tokens": 500,
                "output_tokens": 200,
                "cached_input_tokens": 50,
            },
        },
        {
            "timestamp": "2025-02-01T10:00:10Z",
            "token_count": {
                "model": "o4-mini",
                "input_tokens": 1200,
                "output_tokens": 450,
                "cached_input_tokens": 100,
            },
        },
    ]
    extractor = CodexExtractor()
    path = _write_jsonl(lines)
    meta = extractor.extract(path)

    assert meta.session_id == "thread-abc123"
    assert meta.project_path == "/home/user/myapp"
    assert meta.project_name == "myapp"
    assert meta.agent_version == "0.1.0"
    assert meta.agent_type == "codex_cli"
    assert meta.permission_mode == "auto-edit"
    assert meta.message_count == 2  # 1 user + 1 agent
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 1
    assert meta.tool_call_count == 2  # exec_command + apply_patch
    assert meta.tool_counts["exec_command"] == 1
    assert meta.tool_counts["apply_patch"] == 1
    assert meta.first_prompt == "Fix the auth middleware"
    # Token deltas: first event = 500/200/50, second = 700/250/50
    assert meta.input_tokens == 1200
    assert meta.output_tokens == 450
    assert meta.cache_read_tokens == 100
    assert meta.primary_model == "o4-mini"
    assert meta.duration_seconds == 10.0


def test_token_delta_computation():
    """Cumulative token events should produce correct deltas."""
    lines = [
        {
            "timestamp": "2025-02-01T10:00:00Z",
            "token_count": {
                "model": "gpt-4.1",
                "input_tokens": 100,
                "output_tokens": 50,
                "cached_input_tokens": 0,
            },
        },
        {
            "timestamp": "2025-02-01T10:00:01Z",
            "token_count": {
                "model": "gpt-4.1",
                "input_tokens": 350,
                "output_tokens": 150,
                "cached_input_tokens": 30,
            },
        },
        {
            "timestamp": "2025-02-01T10:00:02Z",
            "token_count": {
                "model": "gpt-4.1",
                "input_tokens": 600,
                "output_tokens": 300,
                "cached_input_tokens": 80,
            },
        },
    ]
    extractor = CodexExtractor()
    path = _write_jsonl(lines)
    meta = extractor.extract(path)

    assert meta.input_tokens == 600
    assert meta.output_tokens == 300
    assert meta.cache_read_tokens == 80
    assert meta.model_tokens["gpt-4.1"]["input"] == 600
    assert meta.model_tokens["gpt-4.1"]["output"] == 300


def test_to_ingest_payload():
    lines = [
        {
            "timestamp": "2025-02-01T10:00:00Z",
            "SessionMeta": {"id": "thread-xyz", "cwd": "/app", "model": "o3"},
        },
        {
            "timestamp": "2025-02-01T10:00:01Z",
            "EventMsg": {"type": "UserMessage", "text": "Hello"},
        },
    ]
    extractor = CodexExtractor()
    path = _write_jsonl(lines)
    meta = extractor.extract(path)

    payload = meta.to_ingest_payload(api_key="test-key")
    assert payload["agent_type"] == "codex_cli"
    assert payload["api_key"] == "test-key"
    assert payload["session_id"] == "thread-xyz"
    assert payload["message_count"] == 1


def test_discover_sessions(tmp_path):
    """Discover sessions from a mock ~/.codex/sessions/ directory."""
    sessions_dir = tmp_path / ".codex" / "sessions" / "2025" / "02" / "01"
    sessions_dir.mkdir(parents=True)

    rollout = sessions_dir / "rollout-abc.jsonl"
    rollout.write_text(json.dumps({"SessionMeta": {"id": "thread-abc", "cwd": "/project"}}) + "\n")

    from pathlib import Path

    original_home = Path.home

    def mock_home():
        return tmp_path

    Path.home = staticmethod(mock_home)
    try:
        extractor = CodexExtractor()
        sessions = extractor.discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "thread-abc"
        assert sessions[0].agent_type == "codex_cli"
        assert sessions[0].project_path == "/project"
    finally:
        Path.home = original_home


def test_variant_key_formats():
    """Extractor should handle both PascalCase and snake_case variant keys."""
    lines = [
        {
            "timestamp": "2025-02-01T10:00:00Z",
            "session_meta": {"id": "thread-sc", "cwd": "/app", "cli_version": "0.2.0"},
        },
        {
            "timestamp": "2025-02-01T10:00:01Z",
            "turn_context": {"model": "gpt-4.1", "approval_policy": "suggest"},
        },
        {
            "timestamp": "2025-02-01T10:00:02Z",
            "event": {"UserMessage": {"text": "Hello from snake_case"}},
        },
    ]
    extractor = CodexExtractor()
    path = _write_jsonl(lines)
    meta = extractor.extract(path)

    assert meta.session_id == "thread-sc"
    assert meta.agent_version == "0.2.0"
    assert meta.permission_mode == "suggest"
    assert meta.user_message_count == 1
    assert meta.first_prompt == "Hello from snake_case"
