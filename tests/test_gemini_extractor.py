import json
import tempfile

from primer.hook.gemini_extractor import GeminiExtractor


def _write_json(data: dict | list, suffix: str = ".json") -> str:
    """Write JSON data to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
        json.dump(data, tmp)
        return tmp.name


def test_extract_empty_file():
    extractor = GeminiExtractor()
    path = _write_json([])
    meta = extractor.extract(path)
    assert meta.message_count == 0
    assert meta.agent_type == "gemini_cli"


def test_extract_nonexistent_file():
    extractor = GeminiExtractor()
    meta = extractor.extract("/nonexistent/path.json")
    assert meta.message_count == 0
    assert meta.agent_type == "gemini_cli"


def test_extract_basic_session(tmp_path):
    session_file = tmp_path / "session-abc123.json"
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Help me write a unit test"}],
                "timestamp": "2025-02-01T10:00:00Z",
            },
            {
                "role": "model",
                "parts": [
                    {"text": "I'll help you write that test."},
                    {"functionCall": {"name": "read_file", "args": {"path": "test.py"}}},
                ],
                "timestamp": "2025-02-01T10:00:05Z",
            },
            {
                "role": "function",
                "parts": [
                    {
                        "functionResponse": {
                            "name": "read_file",
                            "response": {"content": "def test_foo(): pass"},
                        }
                    }
                ],
            },
            {
                "role": "model",
                "parts": [{"text": "Here's the updated test."}],
                "timestamp": "2025-02-01T10:00:10Z",
            },
        ],
        "usageMetadata": {
            "input_token_count": 800,
            "output_token_count": 300,
            "cached_content_token_count": 100,
        },
        "model": "gemini-2.5-pro",
    }
    session_file.write_text(json.dumps(data))

    extractor = GeminiExtractor()
    meta = extractor.extract(str(session_file))

    assert meta.session_id == "session-abc123"
    assert meta.agent_type == "gemini_cli"
    assert meta.message_count == 3  # 1 user + 2 model
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 2
    assert meta.tool_call_count == 1  # read_file function call
    assert meta.tool_counts["read_file"] == 1
    assert meta.first_prompt == "Help me write a unit test"
    assert meta.input_tokens == 800
    assert meta.output_tokens == 300
    assert meta.cache_read_tokens == 100
    assert meta.primary_model == "gemini-2.5-pro"
    assert meta.duration_seconds == 10.0


def test_extract_contents_as_list():
    """Handle case where the file is just a list of contents (no wrapper)."""
    data = [
        {"role": "user", "parts": [{"text": "Hello"}]},
        {"role": "model", "parts": [{"text": "Hi there!"}]},
    ]
    path = _write_json(data)
    extractor = GeminiExtractor()
    meta = extractor.extract(path)

    assert meta.message_count == 2
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 1


def test_extract_with_camelcase_usage():
    """Handle camelCase usage metadata fields."""
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": "Test"}]},
            {"role": "model", "parts": [{"text": "OK"}]},
        ],
        "usageMetadata": {
            "promptTokenCount": 500,
            "candidatesTokenCount": 200,
            "cachedContentTokenCount": 50,
        },
        "model": "gemini-2.5-flash",
    }
    path = _write_json(data)
    extractor = GeminiExtractor()
    meta = extractor.extract(path)

    assert meta.input_tokens == 500
    assert meta.output_tokens == 200
    assert meta.cache_read_tokens == 50
    assert meta.primary_model == "gemini-2.5-flash"


def test_to_ingest_payload():
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": "Hello"}]},
            {"role": "model", "parts": [{"text": "Hi"}]},
        ],
    }
    path = _write_json(data)
    extractor = GeminiExtractor()
    meta = extractor.extract(path)
    meta.session_id = "session-test"

    payload = meta.to_ingest_payload(api_key="test-key")
    assert payload["agent_type"] == "gemini_cli"
    assert payload["api_key"] == "test-key"
    assert payload["message_count"] == 2


def test_discover_sessions(tmp_path):
    """Discover sessions from a mock ~/.gemini/tmp/ directory."""
    chats_dir = tmp_path / ".gemini" / "tmp" / "abc123hash" / "chats"
    chats_dir.mkdir(parents=True)

    session = chats_dir / "session-xyz789.json"
    session.write_text(
        json.dumps(
            {
                "contents": [
                    {"role": "user", "parts": [{"text": "Hi"}]},
                ]
            }
        )
    )

    from pathlib import Path

    original_home = Path.home

    def mock_home():
        return tmp_path

    Path.home = staticmethod(mock_home)
    try:
        extractor = GeminiExtractor()
        sessions = extractor.discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "session-xyz789"
        assert sessions[0].agent_type == "gemini_cli"
        assert sessions[0].has_facets is False
    finally:
        Path.home = original_home


def test_extract_shared_logs_session(tmp_path):
    log_path = tmp_path / "logs.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "sessionId": "gemini-log-1",
                    "messageId": 0,
                    "type": "user",
                    "message": "Audit this repository",
                    "timestamp": "2025-02-01T10:00:00Z",
                },
                {
                    "sessionId": "gemini-log-1",
                    "messageId": 1,
                    "type": "assistant",
                    "message": "I found a few issues.",
                    "timestamp": "2025-02-01T10:00:05Z",
                    "usageMetadata": {
                        "input_token_count": 120,
                        "output_token_count": 45,
                    },
                    "model": "gemini-2.5-pro",
                },
                {
                    "sessionId": "gemini-log-1",
                    "messageId": 2,
                    "type": "tool_call",
                    "name": "read_file",
                    "timestamp": "2025-02-01T10:00:06Z",
                },
                {
                    "sessionId": "gemini-log-1",
                    "messageId": 3,
                    "type": "tool_result",
                    "toolName": "read_file",
                    "message": "def test_example(): pass",
                    "timestamp": "2025-02-01T10:00:08Z",
                },
                {
                    "sessionId": "gemini-log-2",
                    "messageId": 0,
                    "type": "user",
                    "message": "Ignore me",
                    "timestamp": "2025-02-01T11:00:00Z",
                },
            ]
        )
    )

    extractor = GeminiExtractor()
    meta = extractor.extract(f"{log_path}::gemini-log-1")

    assert meta.session_id == "gemini-log-1"
    assert meta.message_count == 2
    assert meta.user_message_count == 1
    assert meta.assistant_message_count == 1
    assert meta.tool_call_count == 1
    assert meta.tool_counts == {"read_file": 1}
    assert meta.first_prompt == "Audit this repository"
    assert meta.input_tokens == 120
    assert meta.output_tokens == 45
    assert meta.primary_model == "gemini-2.5-pro"
    assert meta.duration_seconds == 8.0


def test_discover_sessions_from_shared_logs(tmp_path):
    logs_dir = tmp_path / ".gemini" / "tmp" / "abc123hash"
    logs_dir.mkdir(parents=True)
    project_path = "/Users/example/current-gemini"
    (logs_dir / "metadata.json").write_text(json.dumps({"project_path": project_path}))
    (logs_dir / "logs.json").write_text(
        json.dumps(
            [
                {
                    "sessionId": "gemini-log-1",
                    "type": "user",
                    "message": "Hello",
                    "timestamp": "2025-02-01T10:00:00Z",
                },
                {
                    "sessionId": "gemini-log-2",
                    "type": "user",
                    "message": "Hi",
                    "timestamp": "2025-02-01T10:05:00Z",
                },
            ]
        )
    )

    from pathlib import Path

    original_home = Path.home

    def mock_home():
        return tmp_path

    Path.home = staticmethod(mock_home)
    try:
        extractor = GeminiExtractor()
        sessions = extractor.discover_sessions()
        assert len(sessions) == 2
        sessions_by_id = {session.session_id: session for session in sessions}
        assert sessions_by_id["gemini-log-1"].transcript_path.endswith("logs.json::gemini-log-1")
        assert sessions_by_id["gemini-log-1"].project_path == project_path
        assert sessions_by_id["gemini-log-1"].agent_type == "gemini_cli"
        assert sessions_by_id["gemini-log-2"].transcript_path.endswith("logs.json::gemini-log-2")
    finally:
        Path.home = original_home


def test_no_tokens_graceful():
    """Sessions without token data should still parse with zero counts."""
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": "Hello"}]},
            {"role": "model", "parts": [{"text": "Hi"}]},
        ],
    }
    path = _write_json(data)
    extractor = GeminiExtractor()
    meta = extractor.extract(path)

    assert meta.input_tokens == 0
    assert meta.output_tokens == 0
    assert meta.cache_read_tokens == 0
    assert meta.message_count == 2


def test_multiple_function_calls():
    """Multiple function calls in a single model message."""
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": "Refactor this"}]},
            {
                "role": "model",
                "parts": [
                    {"functionCall": {"name": "read_file", "args": {"path": "a.py"}}},
                    {"functionCall": {"name": "read_file", "args": {"path": "b.py"}}},
                    {"functionCall": {"name": "write_file", "args": {"path": "c.py"}}},
                ],
            },
        ],
    }
    path = _write_json(data)
    extractor = GeminiExtractor()
    meta = extractor.extract(path)

    assert meta.tool_call_count == 3
    assert meta.tool_counts["read_file"] == 2
    assert meta.tool_counts["write_file"] == 1
