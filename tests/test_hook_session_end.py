import io
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from primer.hook.extractor import SessionMetadata


def _make_stdin(data: dict) -> io.StringIO:
    return io.StringIO(json.dumps(data))


# --- main() tests (Claude, default agent) ---


def test_main_no_api_key(monkeypatch):
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.delenv("PRIMER_DEVICE_TOKEN", raising=False)
    monkeypatch.setenv("PRIMER_API_KEY", "")
    monkeypatch.setattr("sys.argv", ["session_end"])

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_prefers_device_token(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.setenv("PRIMER_DEVICE_TOKEN", "device-123")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-device", "transcript_path": "/test/transcript.jsonl"}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    meta = SessionMetadata(session_id="", message_count=1)
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    kwargs = mock_post.call_args.kwargs
    assert kwargs["headers"] == {"x-device-token": "device-123"}
    assert "api_key" not in kwargs["json"]


def test_main_invalid_stdin(monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr("sys.stdin", io.StringIO("not json {{{"))
    monkeypatch.setattr("sys.argv", ["session_end"])

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_missing_session_id(monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr("sys.stdin", _make_stdin({"transcript_path": "/test/t.jsonl"}))
    monkeypatch.setattr("sys.argv", ["session_end"])

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_cursor_agent_accepted(mock_get_extractor, mock_post, monkeypatch):
    """Cursor is a supported agent — verify the hook processes it successfully."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setenv("PRIMER_SERVER_URL", "http://test:8000")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "cursor-1", "transcript_path": "", "cwd": "/workspace"}),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "cursor"])

    mock_get_extractor.return_value = None
    mock_post.return_value = MagicMock(status_code=202)

    from primer.hook.session_end import main

    main()

    mock_post.assert_called_once()
    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["agent_type"] == "cursor"
    assert call_json["session_id"] == "cursor-1"


def test_main_cursor_billing_mode_api_key(monkeypatch):
    """Cursor billing mode detects OPENAI_API_KEY."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from primer.hook.session_end import _detect_billing_mode

    assert _detect_billing_mode("cursor") == "api_key"


def test_main_cursor_billing_mode_anthropic_key(monkeypatch):
    """Cursor billing mode also detects ANTHROPIC_API_KEY (Cursor supports both)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from primer.hook.session_end import _detect_billing_mode

    assert _detect_billing_mode("cursor") == "api_key"


def test_main_cursor_billing_mode_subscription(monkeypatch):
    """Without API keys, Cursor defaults to subscription."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from primer.hook.session_end import _detect_billing_mode

    assert _detect_billing_mode("cursor") == "subscription"


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_success(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setenv("PRIMER_SERVER_URL", "http://test:8000")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin(
            {
                "session_id": "sess-1",
                "transcript_path": "/test/transcript.jsonl",
                "cwd": "/home/user/project",
            }
        ),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    meta = SessionMetadata(
        session_id="",
        message_count=5,
        tool_call_count=2,
    )
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    mock_get_extractor.assert_called_once_with("claude_code")
    mock_extractor.extract.assert_called_once_with("/test/transcript.jsonl")
    assert meta.session_id == "sess-1"
    assert meta.project_path == "/home/user/project"
    assert meta.project_name == "project"
    mock_post.assert_called_once()


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
def test_main_no_transcript(mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-2", "transcript_path": "", "cwd": "/test/proj"}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["session_id"] == "sess-2"


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_with_facets(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-3", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    meta = SessionMetadata(session_id="")
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = {"outcome": "success", "brief_summary": "Done"}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["facets"]["outcome"] == "success"


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_post_non_200(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-4", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = SessionMetadata(session_id="")
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Server error"
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    # Should not raise, just log
    main()


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_post_request_error(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-5", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = SessionMetadata(session_id="")
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None

    mock_post.side_effect = httpx.RequestError("connection refused")

    from primer.hook.session_end import main

    # Should not raise, just log
    main()


# --- Gemini agent tests ---


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_gemini_agent(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    """--agent gemini dispatches to gemini_cli extractor."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setenv("PRIMER_SERVER_URL", "http://test:8000")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin(
            {
                "session_id": "gem-1",
                "transcript_path": "/test/gemini-session.json",
                "cwd": "/home/user/project",
            }
        ),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "gemini"])

    meta = SessionMetadata(session_id="", agent_type="gemini_cli", message_count=3)
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    mock_get_extractor.assert_called_once_with("gemini_cli")
    mock_extractor.extract.assert_called_once_with("/test/gemini-session.json")
    assert meta.session_id == "gem-1"
    assert meta.agent_type == "gemini_cli"
    # Facets should not be loaded for gemini
    mock_facets.assert_not_called()
    mock_post.assert_called_once()


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_gemini_no_facets(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    """Gemini sessions should not attempt to load facets."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "gem-2", "transcript_path": "/test/t.json", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "gemini"])

    meta = SessionMetadata(session_id="", agent_type="gemini_cli")
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    mock_facets.assert_not_called()
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert "facets" not in payload


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_gemini_billing_mode_api_key(mock_get_extractor, mock_facets, mock_post, monkeypatch):
    """Gemini billing mode detects GOOGLE_API_KEY."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "goog-key-123")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "gem-3", "transcript_path": "/test/t.json", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "gemini"])

    meta = SessionMetadata(session_id="", agent_type="gemini_cli")
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    assert meta.billing_mode == "api_key"


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_gemini_billing_mode_subscription(
    mock_get_extractor, mock_facets, mock_post, monkeypatch
):
    """Gemini billing mode defaults to subscription when no API key env is set."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "gem-4", "transcript_path": "/test/t.json", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "gemini"])

    meta = SessionMetadata(session_id="", agent_type="gemini_cli")
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    assert meta.billing_mode == "subscription"


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_gemini_billing_mode_gemini_api_key(
    mock_get_extractor, mock_facets, mock_post, monkeypatch
):
    """Gemini billing mode also detects GEMINI_API_KEY."""
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key-123")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "gem-5", "transcript_path": "/test/t.json", "cwd": ""}),
    )
    monkeypatch.setattr("sys.argv", ["session_end", "--agent", "gemini"])

    meta = SessionMetadata(session_id="", agent_type="gemini_cli")
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    assert meta.billing_mode == "api_key"
