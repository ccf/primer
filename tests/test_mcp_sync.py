from unittest.mock import MagicMock, patch

from primer.hook.extractor import SessionMetadata
from primer.mcp.reader import LocalSession


def _local(sid, path="/t/t.jsonl"):
    return LocalSession(
        session_id=sid,
        transcript_path=path,
        facets_path=None,
        has_facets=False,
    )


# --- get_server_session_ids ---


@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": "s1"}, {"id": "s2"}]
    mock_get.return_value = mock_resp

    from primer.mcp.sync import get_server_session_ids

    ids = get_server_session_ids("http://test:8000", "key")
    assert ids == {"s1", "s2"}


@patch("primer.mcp.sync.httpx.get")
def test_get_server_session_ids_non_200(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_get.return_value = mock_resp

    from primer.mcp.sync import get_server_session_ids

    ids = get_server_session_ids("http://test:8000", "key")
    assert ids == set()


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
@patch("primer.mcp.sync.extract_from_jsonl")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_uploads_missing(mock_list, mock_server_ids, mock_extract, mock_facets, mock_post):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
        _local("s2", "/t/s2.jsonl"),
    ]
    mock_server_ids.return_value = {"s1"}  # s2 is missing

    meta = SessionMetadata(session_id="")
    mock_extract.return_value = meta
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
@patch("primer.mcp.sync.extract_from_jsonl")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_upload_failure(mock_list, mock_server_ids, mock_extract, mock_facets, mock_post):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
    ]
    mock_server_ids.return_value = set()

    meta = SessionMetadata(session_id="")
    mock_extract.return_value = meta
    mock_facets.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_post.return_value = mock_resp

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["synced"] == 0
    assert result["errors"] == 1


@patch("primer.mcp.sync.extract_from_jsonl")
@patch("primer.mcp.sync.get_server_session_ids")
@patch("primer.mcp.sync.list_local_sessions")
def test_sync_extraction_exception(mock_list, mock_server_ids, mock_extract):
    mock_list.return_value = [
        _local("s1", "/t/s1.jsonl"),
    ]
    mock_server_ids.return_value = set()
    mock_extract.side_effect = RuntimeError("parse failed")

    from primer.mcp.sync import sync_sessions

    result = sync_sessions("http://test:8000", "key")
    assert result["errors"] == 1
    assert result["synced"] == 0
