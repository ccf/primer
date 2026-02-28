import json
import tempfile
from pathlib import Path

from primer.hook.extractor import extract_from_jsonl, load_facets


def _write_jsonl(lines: list[dict]) -> str:
    """Write JSONL lines to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        for line in lines:
            tmp.write(json.dumps(line) + "\n")
        return tmp.name


def test_extract_empty_file():
    path = _write_jsonl([])
    meta = extract_from_jsonl(path)
    assert meta.message_count == 0
    assert meta.tool_call_count == 0


def test_extract_nonexistent_file():
    meta = extract_from_jsonl("/nonexistent/path.jsonl")
    assert meta.message_count == 0


def test_extract_basic_session():
    lines = [
        {
            "type": "system",
            "sessionId": "sess-123",
            "cwd": "/home/user/project",
            "version": "1.0.0",
            "permissionMode": "default",
            "timestamp": "2025-01-15T10:00:00Z",
        },
        {
            "type": "human",
            "message": {"content": "Help me fix the login bug"},
            "timestamp": "2025-01-15T10:00:01Z",
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll help you fix that."},
                    {"type": "tool_use", "name": "Read", "input": {"path": "login.py"}},
                ],
                "model": "claude-sonnet-4-5-20250929",
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "cache_read_input_tokens": 100,
                    "cache_creation_input_tokens": 50,
                },
            },
            "timestamp": "2025-01-15T10:00:05Z",
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"path": "login.py"}},
                    {"type": "tool_use", "name": "Read", "input": {"path": "test.py"}},
                ],
                "model": "claude-sonnet-4-5-20250929",
                "usage": {
                    "input_tokens": 600,
                    "output_tokens": 300,
                },
            },
            "timestamp": "2025-01-15T10:00:10Z",
        },
    ]
    path = _write_jsonl(lines)
    meta = extract_from_jsonl(path)

    assert meta.session_id == "sess-123"
    assert meta.project_path == "/home/user/project"
    assert meta.project_name == "project"
    assert meta.agent_version == "1.0.0"
    assert meta.permission_mode == "default"
    assert meta.message_count == 3  # 1 human + 2 assistant
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 2
    assert meta.tool_call_count == 3  # Read + Edit + Read
    assert meta.tool_counts["Read"] == 2
    assert meta.tool_counts["Edit"] == 1
    assert meta.input_tokens == 1100
    assert meta.output_tokens == 500
    assert meta.cache_read_tokens == 100
    assert meta.cache_creation_tokens == 50
    assert meta.primary_model == "claude-sonnet-4-5-20250929"
    assert meta.first_prompt == "Help me fix the login bug"
    assert meta.duration_seconds == 10.0


def test_extract_to_ingest_payload():
    lines = [
        {"type": "human", "message": {"content": "Hello"}, "timestamp": "2025-01-15T10:00:00Z"},
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Hi"}],
                "model": "claude-sonnet-4-5-20250929",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
            "timestamp": "2025-01-15T10:00:01Z",
        },
    ]
    path = _write_jsonl(lines)
    meta = extract_from_jsonl(path)
    meta.session_id = "test-session"

    payload = meta.to_ingest_payload(api_key="test-key")
    assert payload["session_id"] == "test-session"
    assert payload["api_key"] == "test-key"
    assert payload["message_count"] == 2
    assert len(payload["model_usages"]) == 1
    assert payload["model_usages"][0]["model_name"] == "claude-sonnet-4-5-20250929"


def test_load_facets_nonexistent():
    result = load_facets("nonexistent-session-id")
    assert result is None


def test_extract_blank_lines():
    """Blank lines in JSONL are skipped."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        tmp.write('{"type": "human", "message": {"content": "Hi"}}\n')
        tmp.write("\n")
        tmp.write("   \n")
        line = '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}'
        tmp.write(line + "\n")
        path = tmp.name
    meta = extract_from_jsonl(path)
    assert meta.message_count == 2


def test_extract_malformed_json():
    """Invalid JSON lines are skipped gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        tmp.write('{"type": "human", "message": {"content": "Hi"}}\n')
        tmp.write("not valid json {{\n")
        tmp.write('{"type": "assistant", "message": {"content": "Bye"}}\n')
        path = tmp.name
    meta = extract_from_jsonl(path)
    assert meta.message_count == 2


def test_extract_text_string_content():
    """Content as a plain string is extracted."""
    from primer.hook.extractor import _extract_text

    entry = {"message": {"content": "Hello world"}}
    assert _extract_text(entry) == "Hello world"


def test_extract_text_list_with_strings():
    """Content list with bare string items."""
    from primer.hook.extractor import _extract_text

    entry = {"message": {"content": ["Hello", "World"]}}
    assert _extract_text(entry) == "Hello World"


def test_parse_timestamp_invalid():
    """Malformed timestamp doesn't crash."""
    from primer.hook.extractor import _parse_timestamp

    result = _parse_timestamp({"timestamp": "not-a-date"})
    assert result is None
    result2 = _parse_timestamp({"createdAt": 12345})
    assert result2 is None


def test_load_facets_corrupt_json(tmp_path):
    """Returns None on bad JSON in facets file."""
    facets_dir = tmp_path / ".claude" / "usage-data" / "facets"
    facets_dir.mkdir(parents=True)
    facets_file = facets_dir / "corrupt-session.json"
    facets_file.write_text("{not valid json")

    original_home = Path.home

    def mock_home():
        return tmp_path

    Path.home = staticmethod(mock_home)
    try:
        result = load_facets("corrupt-session")
        assert result is None
    finally:
        Path.home = original_home


def test_load_facets(tmp_path):
    facets_dir = tmp_path / ".claude" / "usage-data" / "facets"
    facets_dir.mkdir(parents=True)
    facets_file = facets_dir / "test-session.json"
    facets_file.write_text(
        json.dumps(
            {
                "underlyingGoal": "Fix a bug",
                "outcome": "success",
                "sessionType": "debugging",
                "briefSummary": "Fixed the null pointer bug",
                "frictionCounts": {"tool_error": 2},
            }
        )
    )

    # Monkey-patch Path.home for this test
    original_home = Path.home

    def mock_home():
        return tmp_path

    Path.home = staticmethod(mock_home)
    try:
        result = load_facets("test-session")
        assert result is not None
        assert result["underlying_goal"] == "Fix a bug"
        assert result["outcome"] == "success"
        assert result["friction_counts"] == {"tool_error": 2}
    finally:
        Path.home = original_home


def test_extract_task_with_subagent_type():
    """Task tool_use with subagent_type gets enriched to 'Task:explore'."""
    lines = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {"subagent_type": "explore", "prompt": "find files"},
                    }
                ],
            },
        },
    ]
    path = _write_jsonl(lines)
    meta = extract_from_jsonl(path)
    assert "Task:explore" in meta.tool_counts
    assert meta.tool_counts["Task:explore"] == 1
    assert meta.tool_call_count == 1


def test_extract_skill_with_name():
    """Skill tool_use with skill name gets enriched to 'Skill:commit'."""
    lines = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": "commit"},
                    }
                ],
            },
        },
    ]
    path = _write_jsonl(lines)
    meta = extract_from_jsonl(path)
    assert "Skill:commit" in meta.tool_counts
    assert meta.tool_counts["Skill:commit"] == 1


def test_extract_task_without_subagent_type():
    """Task tool_use without subagent_type stays as plain 'Task'."""
    lines = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {"prompt": "do something"},
                    }
                ],
            },
        },
    ]
    path = _write_jsonl(lines)
    meta = extract_from_jsonl(path)
    assert "Task" in meta.tool_counts
    assert meta.tool_counts["Task"] == 1
