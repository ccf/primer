"""Tests for facet extraction service."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from primer.common.models import Session as SessionModel
from primer.common.models import SessionFacets, SessionMessage
from primer.common.schemas import SessionFacetsPayload, SessionFacetsResponse
from primer.server.services.facet_extraction_service import (
    EXTRACTION_PROMPT,
    _build_transcript_text,
    _facets_dict_to_payload,
    _parse_facets_response,
    extract_and_store_facets,
    extract_facets_from_messages,
)
from primer.server.services.ingest_service import upsert_facets

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
        "confidence_score": 0.82,
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


class TestExtractionPrompt:
    def test_requests_canonical_outcomes(self):
        assert '"outcome": "success|partial|failure"' in EXTRACTION_PROMPT
        assert (
            "fully_achieved|mostly_achieved|partially_achieved|not_achieved"
            not in EXTRACTION_PROMPT
        )

    def test_requests_goal_categories_as_string_list(self):
        assert '"goal_categories": ["category_name", ...]' in EXTRACTION_PROMPT
        assert '{"category_name": count, ...}' not in EXTRACTION_PROMPT

    def test_requests_confidence_score(self):
        assert '"confidence_score"' in EXTRACTION_PROMPT


# --- Payload conversion ---


class TestFacetsDictToPayload:
    def test_extracted_legacy_outcome_is_normalized(self, sample_facets_response):
        payload = _facets_dict_to_payload(sample_facets_response)
        assert payload.outcome == "success"

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
        assert payload.outcome == "success"
        assert payload.confidence_score == 0.82
        assert payload.session_type == "single_task"
        assert payload.agent_helpfulness == "very_helpful"
        assert payload.primary_success == "correct_code_edits"
        assert payload.friction_counts == {}
        assert payload.friction_detail == ""
        assert payload.user_satisfaction_counts == {"satisfied": 1}

    def test_out_of_range_confidence_score_is_dropped(self, sample_facets_response):
        payload = _facets_dict_to_payload({**sample_facets_response, "confidence_score": 1.2})
        assert payload.confidence_score is None

    def test_malformed_string_confidence_score_is_dropped(self, sample_facets_response):
        payload = _facets_dict_to_payload({**sample_facets_response, "confidence_score": "82%"})
        assert payload.confidence_score is None

    def test_unknown_extracted_outcome_is_dropped(self, sample_facets_response):
        payload = _facets_dict_to_payload({**sample_facets_response, "outcome": "abandoned"})
        assert payload.outcome is None

    def test_rejects_scalar_goal_categories(self):
        with pytest.raises(ValidationError):
            _facets_dict_to_payload(
                {
                    "underlying_goal": "test",
                    "goal_categories": "fix_bug",
                    "outcome": "success",
                }
            )

    def test_rejects_mixed_type_goal_category_list(self):
        with pytest.raises(ValidationError):
            _facets_dict_to_payload(
                {
                    "underlying_goal": "test",
                    "goal_categories": ["fix_bug", 3],
                    "outcome": "success",
                }
            )


class TestSessionFacetsPayloadNormalization:
    def test_normalizes_goal_categories_and_outcome(self):
        payload = SessionFacetsPayload(
            underlying_goal="test",
            goal_categories={"fix_bug": 2, "refactor": 1},
            outcome="mostly_achieved",
            confidence_score=0.82,
        )
        assert payload.goal_categories == ["fix_bug", "refactor"]
        assert payload.outcome == "partial"
        assert payload.confidence_score == 0.82

    @pytest.mark.parametrize("value", [True, False])
    def test_rejects_boolean_confidence_score(self, value):
        with pytest.raises(ValidationError):
            SessionFacetsPayload(
                underlying_goal="test",
                goal_categories=["fix_bug"],
                outcome="success",
                confidence_score=value,
            )

    def test_rejects_out_of_range_confidence_score(self):
        with pytest.raises(ValidationError):
            SessionFacetsPayload(
                underlying_goal="test",
                goal_categories=["fix_bug"],
                outcome="success",
                confidence_score=1.2,
            )

    def test_rejects_unknown_outcome(self):
        with pytest.raises(ValidationError):
            SessionFacetsPayload(
                underlying_goal="test",
                goal_categories=["fix_bug"],
                outcome="unexpected_outcome",
            )

    def test_rejects_scalar_goal_categories(self):
        with pytest.raises(ValidationError):
            SessionFacetsPayload(
                underlying_goal="test",
                goal_categories="fix_bug",
                outcome="success",
            )

    def test_rejects_mixed_type_goal_categories(self):
        with pytest.raises(ValidationError):
            SessionFacetsPayload(
                underlying_goal="test",
                goal_categories=["fix_bug", 3],
                outcome="success",
            )


class TestSessionFacetsResponseNormalization:
    def test_normalizes_legacy_orm_backed_values(self, db_session, session_with_messages):
        sid = session_with_messages["session_id"]
        db_session.add(
            SessionFacets(
                session_id=sid,
                goal_categories={"fix_bug": 2, "refactor": 1},
                outcome="mostly_achieved",
                created_at=datetime.now(UTC),
            )
        )
        db_session.flush()

        facets = db_session.query(SessionFacets).filter(SessionFacets.session_id == sid).one()
        response = SessionFacetsResponse.model_validate(facets)

        assert response.goal_categories == ["fix_bug", "refactor"]
        assert response.outcome == "partial"


class TestUpsertFacetsValidation:
    def test_rejects_invalid_confidence_score_from_direct_service_caller(
        self, db_session, session_with_messages
    ):
        sid = session_with_messages["session_id"]
        payload = SessionFacetsPayload.model_construct(
            underlying_goal="test",
            goal_categories=["fix_bug"],
            outcome="success",
            confidence_score=1.2,
        )

        with pytest.raises(ValueError, match="confidence_score"):
            upsert_facets(db_session, sid, payload)

    def test_clears_existing_confidence_score_when_new_payload_has_none(
        self, db_session, session_with_messages
    ):
        sid = session_with_messages["session_id"]
        db_session.add(
            SessionFacets(
                session_id=sid,
                outcome="success",
                confidence_score=0.82,
            )
        )
        db_session.flush()

        upsert_facets(
            db_session,
            sid,
            SessionFacetsPayload(
                underlying_goal="updated",
                goal_categories=["fix_bug"],
                outcome="success",
                confidence_score=None,
            ),
        )

        stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == sid).one()
        assert stored.confidence_score is None


class TestMeasurementIntegrityService:
    def test_measurement_integrity_service_stats_counts_coverage_and_legacy_rows(
        self, db_session, session_with_messages
    ):
        from primer.server.services.measurement_integrity_service import (
            get_measurement_integrity_stats,
        )

        sid = session_with_messages["session_id"]
        session = db_session.query(SessionModel).filter(SessionModel.id == sid).one()
        session.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=sid,
                goal_categories={"fix_bug": 1},
                outcome="mostly_achieved",
                confidence_score=0.4,
            )
        )

        db_session.add(
            SessionModel(
                id=str(uuid.uuid4()),
                engineer_id=session_with_messages["engineer"].id,
                message_count=0,
                user_message_count=0,
                assistant_message_count=0,
                tool_call_count=0,
                input_tokens=0,
                output_tokens=0,
                duration_seconds=30.0,
                started_at=datetime.now(UTC),
                has_facets=False,
            )
        )
        db_session.flush()

        stats = get_measurement_integrity_stats(db_session)
        assert stats["total_sessions"] == 2
        assert stats["sessions_with_messages"] == 1
        assert stats["sessions_with_facets"] == 1
        assert stats["facet_coverage_pct"] == pytest.approx(50.0)
        assert stats["transcript_coverage_pct"] == pytest.approx(50.0)
        assert stats["low_confidence_sessions"] == 1
        assert stats["missing_confidence_sessions"] == 0
        assert stats["legacy_outcome_sessions"] == 1
        assert stats["legacy_goal_category_sessions"] == 1
        assert stats["remaining_legacy_rows"] == 1

    def test_measurement_integrity_service_counts_missing_confidence_scores_as_risk(
        self, db_session, session_with_messages
    ):
        from primer.server.services.measurement_integrity_service import (
            get_measurement_integrity_stats,
        )

        sid = session_with_messages["session_id"]
        session = db_session.query(SessionModel).filter(SessionModel.id == sid).one()
        session.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=sid,
                goal_categories=["fix_bug"],
                outcome="success",
                confidence_score=None,
            )
        )
        db_session.flush()

        stats = get_measurement_integrity_stats(db_session)
        assert stats["sessions_with_facets"] == 1
        assert stats["low_confidence_sessions"] == 0
        assert stats["missing_confidence_sessions"] == 1

    def test_normalize_existing_facets_rewrites_legacy_rows_and_converges_with_limit(
        self, db_session, session_with_messages
    ):
        from primer.server.services.measurement_integrity_service import (
            normalize_existing_facets,
        )

        canonical_session_id = session_with_messages["session_id"]
        canonical_session = (
            db_session.query(SessionModel).filter(SessionModel.id == canonical_session_id).one()
        )
        canonical_session.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=canonical_session_id,
                goal_categories=["fix_bug"],
                outcome="success",
                confidence_score=0.96,
            )
        )

        first_legacy_session_id = str(uuid.uuid4())
        db_session.add(
            SessionModel(
                id=first_legacy_session_id,
                engineer_id=session_with_messages["engineer"].id,
                message_count=1,
                user_message_count=1,
                assistant_message_count=0,
                tool_call_count=0,
                input_tokens=0,
                output_tokens=0,
                duration_seconds=60.0,
                started_at=datetime.now(UTC),
                has_facets=True,
            )
        )
        db_session.flush()
        db_session.add(
            SessionFacets(
                session_id=first_legacy_session_id,
                goal_categories={"fix_bug": 1},
                outcome="mostly_achieved",
                confidence_score=0.45,
            )
        )

        second_legacy_session_id = str(uuid.uuid4())
        db_session.add(
            SessionModel(
                id=second_legacy_session_id,
                engineer_id=session_with_messages["engineer"].id,
                message_count=1,
                user_message_count=1,
                assistant_message_count=0,
                tool_call_count=0,
                input_tokens=0,
                output_tokens=0,
                duration_seconds=60.0,
                started_at=datetime.now(UTC),
                has_facets=True,
            )
        )
        db_session.flush()
        db_session.add(
            SessionFacets(
                session_id=second_legacy_session_id,
                goal_categories={"testing": 1},
                outcome="fully_achieved",
                confidence_score=0.91,
            )
        )
        db_session.flush()

        dry_run = normalize_existing_facets(db_session, limit=2, dry_run=True)
        assert dry_run == {
            "rows_scanned": 2,
            "rows_updated": 0,
            "remaining_legacy_rows": 2,
        }

        canonical_row = (
            db_session.query(SessionFacets)
            .filter(SessionFacets.session_id == canonical_session_id)
            .one()
        )
        first_legacy_row = (
            db_session.query(SessionFacets)
            .filter(SessionFacets.session_id == first_legacy_session_id)
            .one()
        )
        assert canonical_row.outcome == "success"
        assert canonical_row.goal_categories == ["fix_bug"]
        assert first_legacy_row.outcome == "mostly_achieved"
        assert first_legacy_row.goal_categories == {"fix_bug": 1}

        applied = normalize_existing_facets(db_session, limit=1, dry_run=False)
        assert applied == {
            "rows_scanned": 1,
            "rows_updated": 1,
            "remaining_legacy_rows": 1,
        }

        second_applied = normalize_existing_facets(db_session, limit=1, dry_run=False)
        assert second_applied == {
            "rows_scanned": 1,
            "rows_updated": 1,
            "remaining_legacy_rows": 0,
        }

        canonical_row = (
            db_session.query(SessionFacets)
            .filter(SessionFacets.session_id == canonical_session_id)
            .one()
        )
        first_legacy_row = (
            db_session.query(SessionFacets)
            .filter(SessionFacets.session_id == first_legacy_session_id)
            .one()
        )
        second_legacy_row = (
            db_session.query(SessionFacets)
            .filter(SessionFacets.session_id == second_legacy_session_id)
            .one()
        )
        assert canonical_row.outcome == "success"
        assert canonical_row.goal_categories == ["fix_bug"]
        assert first_legacy_row.outcome == "partial"
        assert first_legacy_row.goal_categories == ["fix_bug"]
        assert second_legacy_row.outcome == "success"
        assert second_legacy_row.goal_categories == ["testing"]

    def test_normalize_existing_facets_flushes_without_committing(
        self, db_session, session_with_messages
    ):
        from primer.server.services.measurement_integrity_service import (
            normalize_existing_facets,
        )

        session = (
            db_session.query(SessionModel)
            .filter(SessionModel.id == session_with_messages["session_id"])
            .one()
        )
        session.has_facets = True
        db_session.add(
            SessionFacets(
                session_id=session.id,
                goal_categories={"fix_bug": 1},
                outcome="mostly_achieved",
                confidence_score=0.45,
            )
        )
        db_session.flush()

        original_flush = db_session.flush
        db_session.flush = MagicMock(wraps=original_flush)
        db_session.commit = MagicMock(
            side_effect=AssertionError("normalize_existing_facets should not commit")
        )

        summary = normalize_existing_facets(db_session, limit=1, dry_run=False)

        assert summary == {
            "rows_scanned": 1,
            "rows_updated": 1,
            "remaining_legacy_rows": 0,
        }
        assert db_session.flush.called

        facets = (
            db_session.query(SessionFacets).filter(SessionFacets.session_id == session.id).one()
        )
        assert facets.outcome == "partial"
        assert facets.goal_categories == ["fix_bug"]


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
        assert result.outcome == "success"
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
        assert facets.outcome == "success"
        assert facets.confidence_score == 0.82

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
