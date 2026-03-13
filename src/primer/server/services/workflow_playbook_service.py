from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from primer.common.facet_taxonomy import canonical_outcome, is_success_outcome
from primer.common.models import (
    Engineer,
    SessionCommit,
    SessionFacets,
    SessionWorkflowProfile,
    ToolUsage,
)
from primer.common.models import Session as SessionModel
from primer.common.schemas import WorkflowPlaybook
from primer.server.services.workflow_patterns import (
    infer_workflow_steps,
    workflow_fingerprint_id,
    workflow_fingerprint_label,
)

_MIN_SUPPORTING_SESSIONS = 3
_MIN_SUPPORTING_PEERS = 2


def get_workflow_playbooks(
    db: Session,
    engineer_id: str,
    *,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 3,
) -> list[WorkflowPlaybook]:
    target_sessions = _load_workflow_sessions(
        db,
        engineer_id=engineer_id,
        start_date=start_date,
        end_date=end_date,
    )
    target_fingerprint_counts = Counter(
        session["fingerprint_id"] for session in target_sessions if session["fingerprint_id"]
    )

    if team_id:
        team_playbooks = _derive_playbooks(
            _load_workflow_sessions(
                db,
                exclude_engineer_id=engineer_id,
                team_id=team_id,
                start_date=start_date,
                end_date=end_date,
            ),
            target_fingerprint_counts,
            scope="team",
            limit=limit,
        )
        if team_playbooks:
            return team_playbooks

    return _derive_playbooks(
        _load_workflow_sessions(
            db,
            exclude_engineer_id=engineer_id,
            start_date=start_date,
            end_date=end_date,
        ),
        target_fingerprint_counts,
        scope="org",
        limit=limit,
    )


def _load_workflow_sessions(
    db: Session,
    *,
    engineer_id: str | None = None,
    exclude_engineer_id: str | None = None,
    team_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    query = (
        db.query(
            SessionModel.id,
            SessionModel.engineer_id,
            SessionModel.project_name,
            SessionModel.duration_seconds,
        )
        .join(Engineer, Engineer.id == SessionModel.engineer_id)
        .filter(Engineer.is_active.is_(True))
    )

    if engineer_id:
        query = query.filter(SessionModel.engineer_id == engineer_id)
    if exclude_engineer_id:
        query = query.filter(SessionModel.engineer_id != exclude_engineer_id)
    if team_id:
        query = query.filter(Engineer.team_id == team_id)
    if start_date:
        query = query.filter(SessionModel.started_at >= start_date)
    if end_date:
        query = query.filter(SessionModel.started_at <= end_date)

    session_rows = query.all()
    if not session_rows:
        return []

    session_ids = [row.id for row in session_rows]

    facets_by_session = {
        row.session_id: {
            "session_type": row.session_type,
            "outcome": canonical_outcome(row.outcome),
            "friction_counts": row.friction_counts or {},
        }
        for row in (
            db.query(
                SessionFacets.session_id,
                SessionFacets.session_type,
                SessionFacets.outcome,
                SessionFacets.friction_counts,
            )
            .filter(SessionFacets.session_id.in_(session_ids))
            .all()
        )
    }

    tool_counts_by_session: dict[str, Counter[str]] = defaultdict(Counter)
    for session_id, tool_name, call_count in (
        db.query(ToolUsage.session_id, ToolUsage.tool_name, ToolUsage.call_count)
        .filter(ToolUsage.session_id.in_(session_ids))
        .all()
    ):
        tool_counts_by_session[session_id][tool_name] += call_count

    commit_session_ids = {
        session_id
        for (session_id,) in db.query(SessionCommit.session_id)
        .filter(SessionCommit.session_id.in_(session_ids))
        .distinct()
        .all()
    }
    profiles_by_session = {
        row.session_id: row
        for row in (
            db.query(
                SessionWorkflowProfile.session_id,
                SessionWorkflowProfile.fingerprint_id,
                SessionWorkflowProfile.steps,
            )
            .filter(SessionWorkflowProfile.session_id.in_(session_ids))
            .all()
        )
    }

    enriched_rows = []
    for row in session_rows:
        facets = facets_by_session.get(row.id, {})
        tool_counts = tool_counts_by_session.get(row.id, Counter())
        profile = profiles_by_session.get(row.id)
        steps = list(profile.steps or []) if profile is not None else []
        if not steps:
            steps = infer_workflow_steps(tool_counts, row.id in commit_session_ids)
        session_type = facets.get("session_type")
        fingerprint_id = profile.fingerprint_id if profile is not None else None
        if not fingerprint_id and (session_type or steps):
            fingerprint_id = workflow_fingerprint_id(session_type, steps)
        enriched_rows.append(
            {
                "session_id": row.id,
                "engineer_id": row.engineer_id,
                "project_name": row.project_name,
                "duration_seconds": row.duration_seconds,
                "session_type": session_type,
                "outcome": facets.get("outcome"),
                "friction_counts": facets.get("friction_counts") or {},
                "tool_counts": tool_counts,
                "steps": steps,
                "fingerprint_id": fingerprint_id,
            }
        )

    return enriched_rows


def _derive_playbooks(
    sessions: list[dict],
    target_fingerprint_counts: Counter[str],
    *,
    scope: str,
    limit: int,
) -> list[WorkflowPlaybook]:
    buckets: dict[str, dict] = {}

    for session in sessions:
        fingerprint_id = session["fingerprint_id"]
        if not fingerprint_id:
            continue

        bucket = buckets.setdefault(
            fingerprint_id,
            {
                "session_type": session["session_type"],
                "steps": list(session["steps"]),
                "session_count": 0,
                "peer_ids": set(),
                "success_count": 0,
                "outcome_count": 0,
                "friction_free_count": 0,
                "durations": [],
                "tool_counts": Counter(),
                "friction_counts": Counter(),
                "projects": set(),
            },
        )
        bucket["session_count"] += 1
        bucket["peer_ids"].add(session["engineer_id"])
        if session["duration_seconds"] is not None:
            bucket["durations"].append(session["duration_seconds"])
        bucket["tool_counts"].update(session["tool_counts"])
        bucket["friction_counts"].update(session["friction_counts"])
        if session["project_name"]:
            bucket["projects"].add(session["project_name"])

        outcome = session["outcome"]
        if outcome is not None:
            bucket["outcome_count"] += 1
            if is_success_outcome(outcome):
                bucket["success_count"] += 1

        if not any(count > 0 for count in session["friction_counts"].values()):
            bucket["friction_free_count"] += 1

    playbooks: list[WorkflowPlaybook] = []
    for fingerprint_id, bucket in buckets.items():
        peer_count = len(bucket["peer_ids"])
        if bucket["session_count"] < _MIN_SUPPORTING_SESSIONS or peer_count < _MIN_SUPPORTING_PEERS:
            continue

        success_rate = (
            round(bucket["success_count"] / bucket["outcome_count"], 3)
            if bucket["outcome_count"] > 0
            else None
        )
        if success_rate is not None and success_rate < 0.6:
            continue

        peer_average = bucket["session_count"] / peer_count
        engineer_usage_count = target_fingerprint_counts.get(fingerprint_id, 0)
        if engineer_usage_count == 0:
            adoption_state = "not_used"
        elif engineer_usage_count < peer_average:
            adoption_state = "underused"
        else:
            adoption_state = "already_using"

        title = workflow_fingerprint_label(bucket["session_type"], bucket["steps"])
        summary = _playbook_summary(
            title,
            scope,
            bucket["session_count"],
            peer_count,
            success_rate,
        )
        playbooks.append(
            WorkflowPlaybook(
                playbook_id=f"{scope}:{fingerprint_id}",
                title=title,
                summary=summary,
                scope=scope,
                adoption_state=adoption_state,
                session_type=bucket["session_type"],
                steps=list(bucket["steps"]),
                recommended_tools=[
                    tool_name for tool_name, _ in bucket["tool_counts"].most_common(4)
                ],
                caution_friction_types=[
                    friction for friction, _ in bucket["friction_counts"].most_common(3)
                ],
                example_projects=sorted(bucket["projects"])[:3],
                supporting_session_count=bucket["session_count"],
                supporting_peer_count=peer_count,
                success_rate=success_rate,
                friction_free_rate=round(
                    bucket["friction_free_count"] / bucket["session_count"], 3
                ),
                avg_duration_seconds=(
                    round(sum(bucket["durations"]) / len(bucket["durations"]), 1)
                    if bucket["durations"]
                    else None
                ),
                engineer_usage_count=engineer_usage_count,
            )
        )

    adoption_rank = {"not_used": 0, "underused": 1, "already_using": 2}
    playbooks.sort(
        key=lambda item: (
            adoption_rank.get(item.adoption_state, 3),
            -(item.success_rate or 0.0),
            -item.supporting_peer_count,
            -item.supporting_session_count,
        )
    )
    return playbooks[:limit]


def _playbook_summary(
    title: str,
    scope: str,
    supporting_sessions: int,
    supporting_peers: int,
    success_rate: float | None,
) -> str:
    source_label = "teammates" if scope == "team" else "peers across the org"
    if success_rate is not None:
        return (
            f"{source_label.capitalize()} repeatedly use {title} across "
            f"{supporting_sessions} sessions from {supporting_peers} peers with "
            f"{round(success_rate * 100):.0f}% success."
        )
    return (
        f"{source_label.capitalize()} repeatedly use {title} across "
        f"{supporting_sessions} sessions from {supporting_peers} peers."
    )
