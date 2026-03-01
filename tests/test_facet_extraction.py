"""Tests for facet extraction service."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from primer.common.models import Session as SessionModel
from primer.common.models import SessionFacets, SessionMessage
from primer.server.services.facet_extraction_service import (
    _build_transcript_text,
    _facets_dict_to_payload,
    _parse_facets_response,
    extract_and_store_facets,
    extract_facets_from_messages,
)

# --- Fixtures ---


@pytest.fixture
def sample_messages():
    return [
        {"role": "human", "content_text": "Fix the login bug in auth.py"},
        {
            "role": "assistant",
            "content_text": "I'll look at the auth module.",
            "tool_calls": [{"name": "Read", "input_preview": '{"path": "auth.py"}'}],
        },
        {
            "role": "tool_result",
            "tool_results": [{"name": "Read", "output_preview": "def login():..."}],
        },
        {
            "role": "assistant",
            "content_text": "Found the bug. The session token wasn't being refreshed.",
        },
        {"role": "human", "content_text": "Great, that fixed it. Thanks!"},
    ]


@pytest.fixture
def sample_facets_response():
    return {
        "underlying_goal": "Fix a login bug in the authentication module",
        "goal_categories": {"fix_bug": 1},
        "outcome": "fully_achieved",
        "user_satisfaction_counts": {"satisfied": 1},
        "agent_helpfulness": "very_helpful",
        "session_type": "single_task",
        "friction_counts": {},
        "friction_detail": "",
        "primary_success": "correct_code_edits",
        "brief_summary": "User asked to fix a login bug and it was resolved.",
    }


@pytest.fixture
def session_with_messages(db_session):
    """Create a session with messages but no facets."""
    from primer.common.models import Engineer, Team

    team = Team(name=f"FacetTeam-{uuid.uuid4().hex[:6]}")
    db_session.add(team)
    db_session.flush()

    eng = Engineer(
        name="Facet Tester",
        email=f"facet-{uuid.uuid4().hex[:6]}@example.com",
        api_key_hash="",
        team_id=team.id,
        role="engineer",
    )
    db_session.add(eng)
    db_session.flush()

    sid = str(uuid.uuid4())
    s = SessionModel(
        id=sid,
        engineer_id=eng.id,
        message_count=5,
        user_message_count=2,
        assistant_message_count=2,
        tool_call_count=1,
        input_tokens=1000,
        output_tokens=500,
        duration_seconds=300.0,
        started_at=datetime.now(UTC) - timedelta(hours=1),
        primary_model="claude-sonnet-4-6",
        project_name="test-project",
        first_prompt="Fix the login bug",
        has_facets=False,
    )
    db_session.add(s)
    db_session.flush()

    messages = [
        SessionMessage(session_id=sid, ordinal=0, role="human", content_text="Fix the login bug"),
        SessionMessage(
            session_id=sid,
            ordinal=1,
            role="assistant",
            content_text="Looking at the code.",
            tool_calls=[{"name": "Read", "input_preview": "auth.py"}],
        ),
        SessionMessage(
            session_id=sid,
            ordinal=2,
            role="tool_result",
            tool_results=[{"name": "Read", "output_preview": "def login():..."}],
        ),
        SessionMessage(
            session_id=sid,
            ordinal=3,
            role="assistant",
            content_text="Fixed the bug.",
        ),
        SessionMessage(session_id=sid, ordinal=4, role="human", content_text="Thanks!"),
    ]
    for m in messages:
        db_session.add(m)
    db_session.flush()

    return {"session_id": sid, "engineer": eng, "team": team}


# --- Transcript building ---


class TestBuildTranscript:
    def test_basic_transcript(self, sample_messages):
        text = _build_transcript_text(sample_messages)
        assert "User: Fix the login bug" in text
        assert "Assistant: I'll look at the auth module." in text
        assert "[Tool: Read(" in text
        assert "[Result from Read:" in text
        assert "User: Great, that fixed it." in text

    def test_empty_messages(self):
        assert _build_transcript_text([]) == ""

    def test_truncation(self):
        long_messages = [{"role": "human", "content_text": "x" * 70000}]
        text = _build_transcript_text(long_messages)
        assert len(text) <= 70000
        assert "...[truncated]" in text

    def test_missing_content(self):
        messages = [
            {"role": "human", "content_text": None},
            {"role": "assistant", "content_text": ""},
        ]
        text = _build_transcript_text(messages)
        assert "User: " in text


# --- Response parsing ---


class TestParseFacetsResponse:
    def test_valid_json(self, sample_facets_response):
        text = json.dumps(sample_facets_response)
        result = _parse_facets_response(text)
        assert result is not None
        assert result["outcome"] == "fully_achieved"

    def test_json_with_surrounding_text(self, sample_facets_response):
        text = f"Here are the facets:\n{json.dumps(sample_facets_response)}\nDone."
        result = _parse_facets_response(text)
        assert result is not None

    def test_invalid_json(self):
        assert _parse_facets_response("not json") is None

    def test_missing_required_fields(self):
        result = _parse_facets_response('{"foo": "bar"}')
        assert result is None

    def test_partial_required_fields(self):
        result = _parse_facets_response('{"underlying_goal": "test", "outcome": "success"}')
        assert result is None  # missing brief_summary


# --- Payload conversion ---


class TestFacetsDictToPayload:
    def test_dict_goal_categories_to_list(self):
        data = {
            "underlying_goal": "test",
            "goal_categories": {"fix_bug": 2, "refactor": 1},
            "outcome": "fully_achieved",
        }
        payload = _facets_dict_to_payload(data)
        assert payload.goal_categories == ["fix_bug", "refactor"]

    def test_list_goal_categories_preserved(self):
        data = {
            "underlying_goal": "test",
            "goal_categories": ["fix_bug", "refactor"],
        }
        payload = _facets_dict_to_payload(data)
        assert payload.goal_categories == ["fix_bug", "refactor"]

    def test_all_fields_mapped(self, sample_facets_response):
        payload = _facets_dict_to_payload(sample_facets_response)
        assert payload.underlying_goal == "Fix a login bug in the authentication module"
        assert payload.outcome == "fully_achieved"
        assert payload.session_type == "single_task"
        assert payload.agent_helpfulness == "very_helpful"
        assert payload.primary_success == "correct_code_edits"
        assert payload.friction_counts == {}
        assert payload.friction_detail == ""
        assert payload.user_satisfaction_counts == {"satisfied": 1}


# --- API call ---


class TestExtractFacetsFromMessages:
    def test_no_api_key(self, sample_messages):
        with patch("primer.server.services.facet_extraction_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            result = extract_facets_from_messages(sample_messages)
        assert result is None

    def test_successful_extraction(self, sample_messages, sample_facets_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": json.dumps(sample_facets_response)}]
        }

        with patch("primer.server.services.facet_extraction_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_model = "claude-haiku-4-5-20251001"
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.post.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                result = extract_facets_from_messages(sample_messages)

        assert result is not None
        assert result.outcome == "fully_achieved"
        assert result.underlying_goal == "Fix a login bug in the authentication module"
        assert result.goal_categories == ["fix_bug"]

    def test_api_error(self, sample_messages):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("primer.server.services.facet_extraction_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_model = "claude-haiku-4-5-20251001"
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.post.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                result = extract_facets_from_messages(sample_messages)

        assert result is None

    def test_malformed_llm_response(self, sample_messages):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": [{"type": "text", "text": "I cannot do that."}]}

        with patch("primer.server.services.facet_extraction_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_model = "claude-haiku-4-5-20251001"
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.post.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                result = extract_facets_from_messages(sample_messages)

        assert result is None


# --- Store facets ---


class TestExtractAndStoreFacets:
    def test_stores_facets(self, db_session, session_with_messages, sample_facets_response):
        sid = session_with_messages["session_id"]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": json.dumps(sample_facets_response)}]
        }

        svc = "primer.server.services.facet_extraction_service"
        with (
            patch(f"{svc}.settings") as mock_settings,
            patch("httpx.Client") as mock_client_cls,
            patch(f"{svc}.SessionLocal", return_value=db_session),
        ):
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_model = "claude-haiku-4-5-20251001"
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            # Prevent the test session from being closed
            db_session.close = MagicMock()
            db_session.commit = MagicMock()

            messages = [
                {"role": "human", "content_text": "Fix the login bug"},
                {"role": "assistant", "content_text": "Fixed it."},
            ]
            result = extract_and_store_facets(sid, messages)

        assert result is True

        facets = db_session.query(SessionFacets).filter(SessionFacets.session_id == sid).first()
        assert facets is not None
        assert facets.outcome == "fully_achieved"

    def test_skips_existing_facets(self, db_session, session_with_messages):
        sid = session_with_messages["session_id"]

        # Pre-add facets
        session = db_session.query(SessionModel).filter(SessionModel.id == sid).first()
        session.has_facets = True
        db_session.add(SessionFacets(session_id=sid, outcome="partial"))
        db_session.flush()

        svc = "primer.server.services.facet_extraction_service"
        with (
            patch(f"{svc}.settings") as mock_settings,
            patch(f"{svc}.SessionLocal", return_value=db_session),
        ):
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_model = "claude-haiku-4-5-20251001"
            db_session.close = MagicMock()

            result = extract_and_store_facets(sid, [{"role": "human", "content_text": "hi"}])

        assert result is False


# --- Backfill admin endpoint ---


class TestBackfillEndpoint:
    def test_requires_admin(self, client):
        resp = client.post("/api/v1/admin/backfill-facets")
        assert resp.status_code in (401, 403)

    def test_returns_started(self, client, admin_headers):
        svc = "primer.server.services.facet_extraction_service"
        with (
            patch("primer.server.routers.admin.settings") as mock_settings,
            patch(f"{svc}.SessionLocal"),  # prevent background task hitting real DB
        ):
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_enabled = True
            resp = client.post(
                "/api/v1/admin/backfill-facets?limit=10",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"

    def test_no_api_key_error(self, client, admin_headers):
        with patch("primer.server.routers.admin.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            resp = client.post(
                "/api/v1/admin/backfill-facets",
                headers=admin_headers,
            )
        assert resp.status_code == 422
        assert "ANTHROPIC_API_KEY" in resp.json()["detail"]

    def test_disabled_error(self, client, admin_headers):
        with patch("primer.server.routers.admin.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.facet_extraction_enabled = False
            resp = client.post(
                "/api/v1/admin/backfill-facets",
                headers=admin_headers,
            )
        assert resp.status_code == 422
        assert "disabled" in resp.json()["detail"]
