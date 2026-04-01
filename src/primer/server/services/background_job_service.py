from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_

from primer.common.config import settings
from primer.common.database import SessionLocal
from primer.common.models import BackgroundJob

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_FAILED = "failed"

JOB_TYPE_FACET_EXTRACTION = "facet_extract_session"
JOB_TYPE_FACET_BACKFILL = "facet_backfill"
JOB_TYPE_NARRATIVE_REFRESH_ALL = "narrative_refresh_all"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def enqueue_background_job(
    db,
    *,
    job_type: str,
    payload: dict[str, Any] | None = None,
    created_by_engineer_id: str | None = None,
    max_attempts: int = 3,
) -> BackgroundJob:
    job = BackgroundJob(
        job_type=job_type,
        payload=payload,
        created_by_engineer_id=created_by_engineer_id,
        max_attempts=max_attempts,
    )
    db.add(job)
    db.flush()
    return job


def list_background_jobs(
    db,
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[BackgroundJob]:
    query = db.query(BackgroundJob)
    if status:
        query = query.filter(BackgroundJob.status == status)
    return query.order_by(BackgroundJob.enqueued_at.desc()).limit(limit).all()


def get_background_job_counts(db) -> dict[str, int]:
    rows = (
        db.query(BackgroundJob.status, func.count(BackgroundJob.id))
        .group_by(BackgroundJob.status)
        .all()
    )
    counts = {status: count for status, count in rows}
    return {
        "pending": counts.get(JOB_STATUS_PENDING, 0),
        "running": counts.get(JOB_STATUS_RUNNING, 0),
        "failed": counts.get(JOB_STATUS_FAILED, 0),
    }


def ensure_recurring_jobs(db) -> None:
    if not settings.narrative_auto_refresh or not settings.anthropic_api_key:
        return

    active_count = (
        db.query(func.count(BackgroundJob.id))
        .filter(
            BackgroundJob.job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL,
            BackgroundJob.status.in_([JOB_STATUS_PENDING, JOB_STATUS_RUNNING]),
        )
        .scalar()
        or 0
    )
    if active_count > 0:
        return

    latest_completed = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL,
            BackgroundJob.status == JOB_STATUS_SUCCEEDED,
        )
        .order_by(BackgroundJob.finished_at.desc())
        .first()
    )
    now = _utcnow_naive()
    if latest_completed and latest_completed.finished_at:
        ttl = timedelta(hours=settings.narrative_cache_ttl_hours)
        if latest_completed.finished_at > now - ttl:
            return

    enqueue_background_job(db, job_type=JOB_TYPE_NARRATIVE_REFRESH_ALL)
    db.commit()


def run_background_job_cycle(
    db: Session | None = None,
    *,
    limit: int | None = None,
    lease_seconds: int | None = None,
) -> dict[str, int]:
    processed = 0
    succeeded = 0
    failed = 0
    cycle_limit = limit or settings.background_job_batch_size
    cycle_lease = lease_seconds or settings.background_job_lease_seconds

    for _ in range(cycle_limit):
        claimed = _claim_next_job(db=db, lease_seconds=cycle_lease)
        if claimed is None:
            break

        processed += 1
        job_id, job_type, payload, attempts, max_attempts = claimed
        try:
            _run_job(db, job_type, payload or {})
            _mark_job_succeeded(db, job_id)
            succeeded += 1
        except Exception as exc:
            _mark_job_failed(
                db,
                job_id,
                str(exc),
                attempts=attempts,
                max_attempts=max_attempts,
            )
            failed += 1

    return {"processed": processed, "succeeded": succeeded, "failed": failed}


def _claim_next_job(
    db: Session | None,
    *,
    lease_seconds: int,
) -> tuple[str, str, dict[str, Any] | None, int, int] | None:
    now = _utcnow_naive()
    lease_expires_at = now + timedelta(seconds=lease_seconds)

    owns_session = db is None
    job_db = db or SessionLocal()
    try:
        candidate = (
            job_db.query(BackgroundJob)
            .filter(
                or_(
                    BackgroundJob.status == JOB_STATUS_PENDING,
                    and_(
                        BackgroundJob.status == JOB_STATUS_RUNNING,
                        BackgroundJob.lease_expires_at.is_not(None),
                        BackgroundJob.lease_expires_at < now,
                    ),
                )
            )
            .order_by(BackgroundJob.enqueued_at.asc())
            .first()
        )
        if candidate is None:
            return None

        updated = (
            job_db.query(BackgroundJob)
            .filter(
                BackgroundJob.id == candidate.id,
                or_(
                    BackgroundJob.status == JOB_STATUS_PENDING,
                    and_(
                        BackgroundJob.status == JOB_STATUS_RUNNING,
                        BackgroundJob.lease_expires_at.is_not(None),
                        BackgroundJob.lease_expires_at < now,
                    ),
                ),
            )
            .update(
                {
                    "status": JOB_STATUS_RUNNING,
                    "attempts": candidate.attempts + 1,
                    "started_at": candidate.started_at or now,
                    "finished_at": None,
                    "lease_expires_at": lease_expires_at,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            job_db.rollback()
            return None
        new_attempts = candidate.attempts + 1
        job_db.commit()
        return (
            candidate.id,
            candidate.job_type,
            candidate.payload,
            new_attempts,
            candidate.max_attempts,
        )
    finally:
        if owns_session:
            job_db.close()


def _mark_job_succeeded(db: Session | None, job_id: str) -> None:
    owns_session = db is None
    job_db = db or SessionLocal()
    try:
        now = _utcnow_naive()
        job_db.query(BackgroundJob).filter(BackgroundJob.id == job_id).update(
            {
                "status": JOB_STATUS_SUCCEEDED,
                "lease_expires_at": None,
                "finished_at": now,
                "last_error": None,
            },
            synchronize_session=False,
        )
        job_db.commit()
    finally:
        if owns_session:
            job_db.close()


def _mark_job_failed(
    db: Session | None,
    job_id: str,
    error: str,
    *,
    attempts: int,
    max_attempts: int,
) -> None:
    owns_session = db is None
    job_db = db or SessionLocal()
    try:
        status = JOB_STATUS_FAILED if attempts >= max_attempts else JOB_STATUS_PENDING
        finished_at = _utcnow_naive() if status == JOB_STATUS_FAILED else None
        job_db.rollback()
        job_db.query(BackgroundJob).filter(BackgroundJob.id == job_id).update(
            {
                "status": status,
                "lease_expires_at": None,
                "finished_at": finished_at,
                "last_error": error[:2000],
            },
            synchronize_session=False,
        )
        job_db.commit()
    finally:
        if owns_session:
            job_db.close()


def _run_job(db: Session | None, job_type: str, payload: dict[str, Any]) -> None:
    if job_type == JOB_TYPE_FACET_EXTRACTION:
        from primer.server.services.facet_extraction_service import (
            extract_and_store_facets_for_session,
        )

        result = extract_and_store_facets_for_session(payload["session_id"])
        if result == "failed":
            raise RuntimeError(f"Facet extraction failed for session {payload['session_id']}")
        return

    if job_type == JOB_TYPE_FACET_BACKFILL:
        from primer.server.services.facet_extraction_service import backfill_facets

        backfill_facets(limit=int(payload.get("limit", 50)))
        return

    if job_type == JOB_TYPE_NARRATIVE_REFRESH_ALL:
        from primer.server.services.narrative_service import refresh_all_narratives

        owns_session = db is None
        narrative_db = db or SessionLocal()
        try:
            refresh_all_narratives(narrative_db)
        finally:
            if owns_session:
                narrative_db.close()
        return

    raise ValueError(f"Unsupported background job type: {job_type}")
