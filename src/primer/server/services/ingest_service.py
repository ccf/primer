import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import (
    validate_inbound_goal_categories,
    validate_inbound_outcome,
)
from primer.common.models import (
    GitRepository,
    IngestEvent,
    ModelUsage,
    SessionChangeShape,
    SessionCommit,
    SessionExecutionEvidence,
    SessionFacets,
    SessionMessage,
    SessionRecoveryPath,
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.common.models import (
    Session as SessionModel,
)
from primer.common.schemas import SessionFacetsPayload, SessionIngestPayload
from primer.common.utils import parse_repo_full_name
from primer.server.services.change_shape_service import extract_change_shape
from primer.server.services.execution_evidence_service import extract_execution_evidence
from primer.server.services.recovery_path_service import extract_recovery_path
from primer.server.services.workflow_profile_service import extract_session_workflow_profile

logger = logging.getLogger(__name__)


def _validate_confidence_score(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("confidence_score must be between 0.0 and 1.0")

    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence_score must be between 0.0 and 1.0") from exc

    if not 0.0 <= score <= 1.0:
        raise ValueError("confidence_score must be between 0.0 and 1.0")
    return score


def find_or_create_repository(db: Session, full_name: str) -> GitRepository:
    """Find or create a GitRepository by full_name (handles concurrent inserts)."""
    repo = db.query(GitRepository).filter(GitRepository.full_name == full_name).first()
    if repo:
        return repo
    try:
        with db.begin_nested():
            repo = GitRepository(full_name=full_name)
            db.add(repo)
        return repo
    except IntegrityError:
        return db.query(GitRepository).filter(GitRepository.full_name == full_name).one()


def upsert_session(db: Session, engineer_id: str, payload: SessionIngestPayload) -> bool:
    """Upsert a session and its related data. Returns True if newly created."""
    existing = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    created = existing is None

    if existing:
        session = existing
    else:
        session = SessionModel(id=payload.session_id, engineer_id=engineer_id)
        db.add(session)

    # Update scalar fields
    for field in [
        "agent_type",
        "project_path",
        "project_name",
        "git_branch",
        "agent_version",
        "permission_mode",
        "end_reason",
        "started_at",
        "ended_at",
        "duration_seconds",
        "message_count",
        "user_message_count",
        "assistant_message_count",
        "tool_call_count",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_creation_tokens",
        "primary_model",
        "billing_mode",
        "summary",
    ]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(session, field, value)

    # Truncate first_prompt
    if payload.first_prompt:
        session.first_prompt = payload.first_prompt[:500]

    # Repository linking
    if payload.git_remote_url:
        full_name = parse_repo_full_name(payload.git_remote_url)
        if full_name:
            repo = find_or_create_repository(db, full_name)
            session.repository_id = repo.id

    # Tool usages — replace all
    if payload.tool_usages is not None:
        db.query(ToolUsage).filter(ToolUsage.session_id == session.id).delete()
        for tu in payload.tool_usages:
            db.add(
                ToolUsage(
                    session_id=session.id,
                    tool_name=tu.tool_name,
                    call_count=tu.call_count,
                )
            )

    # Model usages — replace all
    if payload.model_usages is not None:
        db.query(ModelUsage).filter(ModelUsage.session_id == session.id).delete()
        for mu in payload.model_usages:
            db.add(
                ModelUsage(
                    session_id=session.id,
                    model_name=mu.model_name,
                    input_tokens=mu.input_tokens,
                    output_tokens=mu.output_tokens,
                    cache_read_tokens=mu.cache_read_tokens,
                    cache_creation_tokens=mu.cache_creation_tokens,
                )
            )

    # Commits — replace all
    if payload.commits is not None:
        db.query(SessionCommit).filter(SessionCommit.session_id == session.id).delete()
        for c in payload.commits:
            db.add(
                SessionCommit(
                    session_id=session.id,
                    repository_id=session.repository_id,
                    commit_sha=c.sha,
                    commit_message=c.message,
                    author_name=c.author_name,
                    author_email=c.author_email,
                    committed_at=c.committed_at,
                    files_changed=c.files_changed,
                    lines_added=c.lines_added,
                    lines_deleted=c.lines_deleted,
                )
            )

    # Messages
    if payload.messages is not None:
        db.query(SessionMessage).filter(SessionMessage.session_id == session.id).delete()
        for msg in payload.messages:
            db.add(SessionMessage(session_id=session.id, **msg.model_dump()))

        db.query(SessionExecutionEvidence).filter(
            SessionExecutionEvidence.session_id == session.id
        ).delete()
        for evidence in extract_execution_evidence(payload.messages):
            db.add(
                SessionExecutionEvidence(
                    session_id=session.id,
                    ordinal=evidence.ordinal,
                    evidence_type=evidence.evidence_type,
                    status=evidence.status,
                    tool_name=evidence.tool_name,
                    command=evidence.command,
                    output_preview=evidence.output_preview,
                )
            )

    if payload.messages is not None or payload.commits is not None:
        _upsert_change_shape(db, session.id)

    # Facets
    if payload.facets:
        upsert_facets(db, session.id, payload.facets)
        session.has_facets = True

    if payload.messages is not None or payload.facets is not None:
        _upsert_recovery_path(db, session.id)

    _upsert_workflow_profile(db, session.id)

    db.flush()
    return created


def upsert_facets(db: Session, session_id: str, facets: SessionFacetsPayload) -> None:
    """Upsert facets for a session."""
    validated_values = {
        "goal_categories": validate_inbound_goal_categories(
            getattr(facets, "goal_categories", None)
        ),
        "outcome": validate_inbound_outcome(getattr(facets, "outcome", None)),
        "confidence_score": _validate_confidence_score(getattr(facets, "confidence_score", None)),
    }

    existing = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    if existing:
        record = existing
    else:
        record = SessionFacets(session_id=session_id)
        db.add(record)

    for field in [
        "underlying_goal",
        "goal_categories",
        "outcome",
        "confidence_score",
        "session_type",
        "primary_success",
        "agent_helpfulness",
        "brief_summary",
        "user_satisfaction_counts",
        "friction_counts",
        "friction_detail",
    ]:
        value = validated_values.get(field, getattr(facets, field, None))
        if field == "confidence_score":
            setattr(record, field, value)
            continue
        if value is not None:
            setattr(record, field, value)

    db.flush()


def _upsert_change_shape(db: Session, session_id: str) -> None:
    db.flush()

    messages = (
        db.query(SessionMessage)
        .filter(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.ordinal)
        .all()
    )
    commits = db.query(SessionCommit).filter(SessionCommit.session_id == session_id).all()
    derived = extract_change_shape(messages, commits)

    existing = (
        db.query(SessionChangeShape).filter(SessionChangeShape.session_id == session_id).first()
    )
    if derived is None:
        if existing is not None:
            db.delete(existing)
            db.flush()
        return

    record = existing or SessionChangeShape(session_id=session_id)
    if existing is None:
        db.add(record)

    record.files_touched_count = derived.files_touched_count
    record.named_touched_files = derived.named_touched_files
    record.commit_files_changed = derived.commit_files_changed
    record.lines_added = derived.lines_added
    record.lines_deleted = derived.lines_deleted
    record.diff_size = derived.diff_size
    record.edit_operations = derived.edit_operations
    record.create_operations = derived.create_operations
    record.delete_operations = derived.delete_operations
    record.rename_operations = derived.rename_operations
    record.churn_files_count = derived.churn_files_count
    record.rewrite_indicator = derived.rewrite_indicator
    record.revert_indicator = derived.revert_indicator
    db.flush()


def _upsert_recovery_path(db: Session, session_id: str) -> None:
    db.flush()

    messages = (
        db.query(SessionMessage)
        .filter(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.ordinal)
        .all()
    )
    execution_evidence = (
        db.query(SessionExecutionEvidence)
        .filter(SessionExecutionEvidence.session_id == session_id)
        .order_by(SessionExecutionEvidence.ordinal)
        .all()
    )
    facets = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    derived = extract_recovery_path(messages, execution_evidence, facets)

    existing = (
        db.query(SessionRecoveryPath).filter(SessionRecoveryPath.session_id == session_id).first()
    )
    if derived is None:
        if existing is not None:
            db.delete(existing)
            db.flush()
        return

    record = existing or SessionRecoveryPath(session_id=session_id)
    if existing is None:
        db.add(record)

    record.friction_detected = derived.friction_detected
    record.first_friction_ordinal = derived.first_friction_ordinal
    record.recovery_step_count = derived.recovery_step_count
    record.recovery_strategies = derived.recovery_strategies
    record.recovery_result = derived.recovery_result
    record.final_outcome = derived.final_outcome
    record.last_verification_status = derived.last_verification_status
    record.sample_recovery_commands = derived.sample_recovery_commands
    db.flush()


def _upsert_workflow_profile(db: Session, session_id: str) -> None:
    db.flush()

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        return

    tool_usages = db.query(ToolUsage).filter(ToolUsage.session_id == session_id).all()
    execution_evidence = (
        db.query(SessionExecutionEvidence)
        .filter(SessionExecutionEvidence.session_id == session_id)
        .order_by(SessionExecutionEvidence.ordinal)
        .all()
    )
    change_shape = (
        db.query(SessionChangeShape).filter(SessionChangeShape.session_id == session_id).first()
    )
    recovery_path = (
        db.query(SessionRecoveryPath).filter(SessionRecoveryPath.session_id == session_id).first()
    )
    facets = db.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    has_commit = db.query(SessionCommit.id).filter(SessionCommit.session_id == session_id).first()
    derived = extract_session_workflow_profile(
        session,
        tool_usages,
        execution_evidence,
        change_shape=change_shape,
        recovery_path=recovery_path,
        facets=facets,
        has_commit=has_commit is not None,
    )

    existing = (
        db.query(SessionWorkflowProfile)
        .filter(SessionWorkflowProfile.session_id == session_id)
        .first()
    )
    if derived is None:
        if existing is not None:
            db.delete(existing)
            db.flush()
        return

    record = existing or SessionWorkflowProfile(session_id=session_id)
    if existing is None:
        db.add(record)

    record.fingerprint_id = derived.fingerprint_id
    record.label = derived.label
    record.steps = derived.steps
    record.archetype = derived.archetype
    record.archetype_source = derived.archetype_source
    record.archetype_reason = derived.archetype_reason
    record.top_tools = derived.top_tools
    record.delegation_count = derived.delegation_count
    record.verification_run_count = derived.verification_run_count
    db.flush()


def log_ingest_event(
    db: Session,
    engineer_id: str,
    event_type: str,
    session_id: str | None,
    payload_size: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    db.add(
        IngestEvent(
            engineer_id=engineer_id,
            event_type=event_type,
            session_id=session_id,
            payload_size_bytes=payload_size,
            status=status,
            error_message=error_message,
        )
    )
    db.flush()
