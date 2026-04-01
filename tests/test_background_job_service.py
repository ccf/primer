from datetime import UTC, datetime, timedelta
from uuid import uuid4

from primer.common.models import BackgroundJob, SessionMessage
from primer.common.models import Session as SessionModel
from primer.server.services.background_job_service import (
    JOB_STATUS_PENDING,
    JOB_STATUS_SUCCEEDED,
    JOB_TYPE_FACET_EXTRACTION,
    JOB_TYPE_NARRATIVE_REFRESH_ALL,
    enqueue_background_job,
    ensure_recurring_jobs,
    run_background_job_cycle,
)


def test_run_background_job_cycle_processes_facet_extraction_job(
    monkeypatch, db_session, engineer_with_key
):
    engineer, _api_key = engineer_with_key
    session = SessionModel(
        id=str(uuid4()),
        engineer_id=engineer.id,
        started_at=datetime.now(UTC),
        message_count=2,
        user_message_count=1,
        assistant_message_count=1,
        duration_seconds=120.0,
        has_facets=False,
    )
    db_session.add(session)
    db_session.flush()
    db_session.add(
        SessionMessage(
            session_id=session.id,
            ordinal=0,
            role="human",
            content_text="Fix the auth bug",
        )
    )
    db_session.flush()

    job = enqueue_background_job(
        db_session,
        job_type=JOB_TYPE_FACET_EXTRACTION,
        payload={"session_id": session.id},
        created_by_engineer_id=engineer.id,
    )
    db_session.commit()

    observed: list[str] = []

    def fake_extract_and_store_facets_for_session(session_id: str) -> bool:
        observed.append(session_id)
        return True

    monkeypatch.setattr(
        "primer.server.services.facet_extraction_service.extract_and_store_facets_for_session",
        fake_extract_and_store_facets_for_session,
    )

    result = run_background_job_cycle(db_session, limit=1, lease_seconds=60)

    assert result == {"processed": 1, "succeeded": 1, "failed": 0}
    assert observed == [session.id]
    db_session.refresh(job)
    assert job.status == JOB_STATUS_SUCCEEDED


def test_ensure_recurring_jobs_enqueues_narrative_refresh(db_session, monkeypatch):
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.narrative_auto_refresh",
        True,
    )
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.anthropic_api_key",
        "test-key",
    )
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.narrative_cache_ttl_hours",
        24,
    )

    ensure_recurring_jobs(db_session)

    job = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL)
        .one()
    )
    assert job.status == JOB_STATUS_PENDING

    ensure_recurring_jobs(db_session)
    assert (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL)
        .count()
        == 1
    )


def test_ensure_recurring_jobs_skips_recent_success(db_session, monkeypatch):
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.narrative_auto_refresh",
        True,
    )
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.anthropic_api_key",
        "test-key",
    )
    monkeypatch.setattr(
        "primer.server.services.background_job_service.settings.narrative_cache_ttl_hours",
        24,
    )

    job = BackgroundJob(
        job_type=JOB_TYPE_NARRATIVE_REFRESH_ALL,
        status=JOB_STATUS_SUCCEEDED,
        finished_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
    )
    db_session.add(job)
    db_session.commit()

    ensure_recurring_jobs(db_session)

    assert (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL)
        .count()
        == 1
    )
