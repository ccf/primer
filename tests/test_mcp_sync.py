from unittest.mock import MagicMock, patch

from primer.hook.extractor import SessionMetadata
from primer.mcp.reader import LocalSession


def _local(sid, path="/t/t.jsonl", agent_type="claude_code"):
    return LocalSession(
        session_id=sid,
        transcript_path=path,
        facets_path=None,
        has_facets=False,
        agent_type=agent_type,
    )


def _make_mock_extractor(meta=None):
    """Create a mock extractor that returns given metadata."""
    ext = MagicMock()
    ext.extract.return_value = meta or SessionMetadata(session_id="")
    return ext


# --- get_server_session_ids ---


@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": [{"id": "s1"}, {"id": "s2"}]}
    mock_get.return_value = mock_resp

    from primer.mcp.sync import get_server_session_ids

    ids = get_server_session_ids("http://test:8000", "key")
    assert ids == {"s1", "s2"}
    assert mock_get.call_args.kwargs["headers"] == {"x-api-key": "key"}
    assert mock_get.call_args.kwargs["params"] == {"limit": 1000, "offset": 0}


@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_non_200(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_get.return_value = mock_resp

    from primer.mcp.sync import get_server_session_ids

    ids = get_server_session_ids("http://test:8000", "key")
    assert ids == set()


@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_paginates(mock_get):
    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "items": [{"id": f"s{i}"} for i in range(1000)],
        "total_count": 1002,
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "items": [{"id": "s1000"}, {"id": "s1001"}],
        "total_count": 1002,
    }
    mock_get.side_effect = [first, second]

    from primer.mcp.sync import get_server_session_ids

    ids = get_server_session_ids("http://test:8000", "key")

    assert len(ids) == 1002
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[0].kwargs["params"] == {"limit": 1000, "offset": 0}
    assert mock_get.call_args_list[1].kwargs["params"] == {"limit": 1000, "offset": 1000}


@patch("primer.mcp.sync.logger")
@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_stops_at_max_pages(mock_get, mock_logger, monkeypatch):
    from primer.mcp import sync

    monkeypatch.setattr(sync, "_MAX_PAGES", 2)

    page = MagicMock()
    page.status_code = 200
    page.json.return_value = {"items": [{"id": "s1"}] * 1000}
    mock_get.side_effect = [page, page]

    ids = sync.get_server_session_ids("http://test:8000", "key")

    assert ids == {"s1"}
    assert mock_get.call_count == 2
    mock_logger.warning.assert_called_once()


# --- sync_sessions ---


@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_no_local_sessions(mock_list, mock_server_ids):
    mock_list.return_value = []

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["local_count"] == 0
    assert result["synced"] == 0
    mock_server_ids.assert_not_called()


@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_all_already_synced(mock_list, mock_server_ids):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
    ]
    mock_server_ids.return_value = {"s1"}

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["already_synced"] == 1
    assert result["synced"] == 0


@patch("primer.mcp.sync.httpx.post")
@patch("primer.mcp.sync.load_facets")
@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_uploads_missing(mock_list, mock_server_ids, mock_get_ext, mock_facets, mock_post):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
        _local("s2", "/t/s2.jsonl"),
    ]
    mock_server_ids.return_value = {"s1"}  # s2 is missing

    meta = SessionMetadata(session_id="")
    mock_get_ext.return_value = _make_mock_extractor(meta)
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["synced"] == 1
    assert result["already_synced"] == 1
    assert result["errors"] == 0


@patch("primer.mcp.sync.httpx.post")
@patch("primer.mcp.sync.load_facets")
@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_updates_legacy_codex_rollout_row_without_duplicate(
    mock_list, mock_server_ids, mock_get_ext, mock_facets, mock_post
):
    mock_list.return_value = [
        LocalSession(
            session_id="thread-uuid",
            transcript_path="/t/rollout-2026-03-08-thread-uuid.jsonl",
            facets_path=None,
            has_facets=False,
            project_path=None,
            agent_type="codex_cli",
        ),
    ]
    mock_server_ids.return_value = {"rollout-2026-03-08-thread-uuid"}

    meta = SessionMetadata(session_id="thread-uuid", agent_type="codex_cli")
    mock_get_ext.return_value = _make_mock_extractor(meta)
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")

    assert result["synced"] == 1
    assert result["already_synced"] == 0
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["session_id"] == "rollout-2026-03-08-thread-uuid"


@patch("primer.mcp.sync.httpx.post")
@patch("primer.mcp.sync.load_facets")
@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_uploads_imported_cursor_session_without_facets(
    mock_list, mock_server_ids, mock_get_ext, mock_facets, mock_post
):
    mock_list.return_value = [
        LocalSession(
            session_id="cursor-1",
            transcript_path="/t/cursor-1.json",
            facets_path=None,
            has_facets=False,
            project_path=None,
            agent_type="cursor",
        ),
    ]
    mock_server_ids.return_value = set()

    meta = SessionMetadata(session_id="", agent_type="cursor")
    mock_get_ext.return_value = _make_mock_extractor(meta)
    mock_facets.return_value = {"outcome": "success"}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")

    assert result["synced"] == 1
    mock_facets.assert_not_called()
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["agent_type"] == "cursor"
    assert "facets" not in payload


@patch("primer.mcp.sync.httpx.post")
@patch("primer.mcp.sync.load_facets")
@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_includes_cursor_facets_when_bundle_provides_them(
    mock_list, mock_server_ids, mock_get_ext, mock_facets, mock_post
):
    mock_list.return_value = [
        LocalSession(
            session_id="cursor-2",
            transcript_path="/t/cursor-2.json",
            facets_path="/workspace/cursor-2-facets.json",
            has_facets=True,
            project_path=None,
            agent_type="cursor",
        ),
    ]
    mock_server_ids.return_value = set()

    meta = SessionMetadata(session_id="", agent_type="cursor")
    mock_get_ext.return_value = _make_mock_extractor(meta)
    mock_facets.return_value = {"outcome": "success"}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")

    assert result["synced"] == 1
    mock_facets.assert_called_once_with("cursor-2", "/workspace/cursor-2-facets.json")
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
    assert payload["agent_type"] == "cursor"
    assert payload["facets"] == {"outcome": "success"}


@patch("primer.mcp.sync.httpx.post")
@patch("primer.mcp.sync.load_facets")
@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_upload_failure(mock_list, mock_server_ids, mock_get_ext, mock_facets, mock_post):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
    ]
    mock_server_ids.return_value = set()

    meta = SessionMetadata(session_id="")
    mock_get_ext.return_value = _make_mock_extractor(meta)
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["synced"] == 0
    assert result["errors"] == 1


@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_extraction_exception(mock_list, mock_server_ids, mock_get_ext):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
    ]
    mock_server_ids.return_value = set()
    mock_ext = MagicMock()
    mock_ext.extract.side_effect = RuntimeError("parse failed")
    mock_get_ext.return_value = mock_ext

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["errors"] == 1
    assert result["synced"] == 0


@patch("primer.mcp.sync.get_extractor_for")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_unknown_agent_type(mock_list, mock_server_ids, mock_get_ext):
    """Unknown agent_type returns None from get_extractor_for, counted as error."""
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl", agent_type="unknown_agent"),
    ]
    mock_server_ids.return_value = set()
    mock_get_ext.return_value = None

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["errors"] == 1
    assert result["synced"] == 0
