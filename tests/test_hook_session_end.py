import io
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from primer.hook.extractor import SessionMetadata


def _make_stdin(data: dict) -> io.StringIO:
    return io.StringIO(json.dumps(data))


# --- main() tests ---


def test_main_no_api_key(monkeypatch):
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.setenv("PRIMER_API_KEY", "")

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_invalid_stdin(monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr("sys.stdin", io.StringIO("not json {{{"))

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_missing_session_id(monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr("sys.stdin", _make_stdin({"transcript_path": "/test/t.jsonl"}))

    from primer.hook.session_end import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.extract_from_jsonl")
def test_main_success(mock_extract, mock_facets, mock_post, monkeypatch):
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

    meta = SessionMetadata(
        session_id="",
        message_count=5,
        tool_call_count=2,
    )
    mock_extract.return_value = meta
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    mock_extract.assert_called_once_with("/test/transcript.jsonl")
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
@patch("primer.hook.session_end.extract_from_jsonl")
def test_main_with_facets(mock_extract, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-3", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )

    meta = SessionMetadata(session_id="")
    mock_extract.return_value = meta
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
@patch("primer.hook.session_end.extract_from_jsonl")
def test_main_post_non_200(mock_extract, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-4", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )

    mock_extract.return_value = SessionMetadata(session_id="")
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
@patch("primer.hook.session_end.extract_from_jsonl")
def test_main_post_request_error(mock_extract, mock_facets, mock_post, monkeypatch):
    monkeypatch.setenv("PRIMER_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-5", "transcript_path": "/test/t.jsonl", "cwd": ""}),
    )

    mock_extract.return_value = SessionMetadata(session_id="")
    mock_facets.return_value = None

    mock_post.side_effect = httpx.RequestError("connection refused")

    from primer.hook.session_end import main

    # Should not raise, just log
    main()
