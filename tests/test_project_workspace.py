from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from primer.common.models import (
    GitRepository,
    PullRequest,
    ReviewFinding,
    SessionCommit,
    SessionFacets,
)


def _ingest_project_session(
    client,
    api_key: str,
    *,
    project_name: str,
    agent_type: str = "claude_code",
    model_name: str = "claude-sonnet-4",
    tool_name: str = "Edit",
    tool_usages: list[dict] | None = None,
    git_remote_url: str | None = None,
    with_commit: bool = False,
    session_type: str = "implementation",
    outcome: str = "success",
    friction_counts: dict[str, int] | None = None,
    friction_detail: str = "Needed to reconcile two competing approaches.",
):
    now = datetime.now(UTC)
    payload = {
        "session_id": str(uuid4()),
        "api_key": api_key,
        "agent_type": agent_type,
        "project_path": str(Path.home() / project_name),
        "project_name": project_name,
        "permission_mode": "on-request",
        "started_at": (now - timedelta(hours=1)).isoformat(),
        "ended_at": now.isoformat(),
        "duration_seconds": 1800,
        "message_count": 2,
        "user_message_count": 1,
        "assistant_message_count": 1,
        "tool_call_count": 3,
        "input_tokens": 1200,
        "output_tokens": 500,
        "primary_model": model_name,
        "messages": [
            {
                "ordinal": 1,
                "role": "human",
                "content_text": f"Work on {project_name}",
            },
            {
                "ordinal": 2,
                "role": "assistant",
                "content_text": "Done",
                "model": model_name,
                "token_count": 200,
            },
        ],
        "tool_usages": tool_usages or [{"tool_name": tool_name, "call_count": 3}],
        "model_usages": [
            {
                "model_name": model_name,
                "input_tokens": 1200,
                "output_tokens": 500,
            }
        ],
        "facets": {
            "outcome": outcome,
            "session_type": session_type,
            "primary_success": "complete",
            "friction_counts": friction_counts or {"context_switching": 1},
            "friction_detail": friction_detail,
        },
        "git_remote_url": git_remote_url,
        "commits": (
            [
                {
                    "sha": f"{uuid4().hex[:12]}",
                    "message": "feat: ship workspace",
                    "committed_at": now.isoformat(),
                    "files_changed": 4,
                    "lines_added": 120,
                    "lines_deleted": 18,
                }
            ]
            if with_commit
            else []
        ),
    }
    response = client.post("/api/v1/ingest/session", json=payload)
    assert response.status_code == 200
    return payload["session_id"]


def _ensure_project_facets(
    db_session,
    session_id: str,
    *,
    session_type: str,
    outcome: str = "success",
    friction_counts: dict[str, int] | None = None,
    friction_detail: str = "Needed to reconcile two competing approaches.",
) -> None:
    record = db_session.query(SessionFacets).filter(SessionFacets.session_id == session_id).first()
    if record is None:
        record = SessionFacets(session_id=session_id)
        db_session.add(record)

    record.outcome = outcome
    record.session_type = session_type
    record.primary_success = "complete"
    record.friction_counts = friction_counts or {"context_switching": 1}
    record.friction_detail = friction_detail


def test_project_workspace_endpoint_returns_composed_views(
    client, engineer_with_key, admin_headers, db_session
):
    engineer, api_key = engineer_with_key

    workspace_session_id = _ingest_project_session(
        client,
        api_key,
        project_name="workspace-proj",
        tool_usages=[
            {"tool_name": "Edit", "call_count": 2},
            {"tool_name": "Bash", "call_count": 1},
        ],
        git_remote_url="https://github.com/acme/workspace.git",
        with_commit=True,
        session_type="implementation",
    )
    codex_session_id = _ingest_project_session(
        client,
        api_key,
        project_name="workspace-proj",
        agent_type="codex_cli",
        model_name="gpt-5.3-codex",
        tool_name="Read",
        tool_usages=[
            {"tool_name": "Grep", "call_count": 2},
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Bash", "call_count": 1},
        ],
        git_remote_url="https://github.com/acme/workspace.git",
        session_type="debugging",
        outcome="failure",
        friction_counts={"tool_error": 2, "context_switching": 1},
        friction_detail="Tooling failed mid-session.",
    )
    other_session_id = _ingest_project_session(
        client,
        api_key,
        project_name="other-proj",
        git_remote_url="https://github.com/acme/other.git",
        with_commit=True,
    )
    _ensure_project_facets(db_session, workspace_session_id, session_type="implementation")
    _ensure_project_facets(
        db_session,
        codex_session_id,
        session_type="debugging",
        outcome="failure",
        friction_counts={"tool_error": 2, "context_switching": 1},
        friction_detail="Tooling failed mid-session.",
    )

    workspace_repo = (
        db_session.query(GitRepository).filter(GitRepository.full_name == "acme/workspace").one()
    )
    workspace_repo.default_branch = "main"
    workspace_repo.has_claude_md = True
    workspace_repo.has_agents_md = True
    workspace_repo.has_claude_dir = False
    workspace_repo.ai_readiness_score = 75.0
    workspace_repo.ai_readiness_checked_at = datetime.now(UTC)
    workspace_pr = PullRequest(
        repository_id=workspace_repo.id,
        engineer_id=engineer.id,
        github_pr_number=101,
        title="Add project workspace",
        state="merged",
        head_branch="feat/workspace",
        additions=120,
        deletions=18,
        review_comments_count=None,
        commits_count=1,
        pr_created_at=datetime.now(UTC) - timedelta(days=1),
        merged_at=datetime.now(UTC) - timedelta(hours=12),
    )
    db_session.add(workspace_pr)
    db_session.flush()

    workspace_commit = (
        db_session.query(SessionCommit)
        .filter(SessionCommit.session_id == workspace_session_id)
        .one()
    )
    workspace_commit.repository_id = workspace_repo.id
    workspace_commit.pull_request_id = workspace_pr.id

    db_session.add(
        ReviewFinding(
            pull_request_id=workspace_pr.id,
            source="bugbot",
            external_id="workspace-finding",
            severity="high",
            title="Fix null handling",
            status="fixed",
            detected_at=datetime.now(UTC) - timedelta(hours=18),
            resolved_at=datetime.now(UTC) - timedelta(hours=8),
        )
    )

    other_repo = (
        db_session.query(GitRepository).filter(GitRepository.full_name == "acme/other").one()
    )
    other_pr = PullRequest(
        repository_id=other_repo.id,
        engineer_id=engineer.id,
        github_pr_number=202,
        title="Unrelated work",
        state="closed",
        head_branch="feat/other",
        additions=44,
        deletions=11,
        review_comments_count=7,
        commits_count=1,
        pr_created_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(other_pr)
    db_session.flush()

    other_commit = (
        db_session.query(SessionCommit).filter(SessionCommit.session_id == other_session_id).one()
    )
    other_commit.repository_id = other_repo.id
    other_commit.pull_request_id = other_pr.id

    db_session.add(
        ReviewFinding(
            pull_request_id=other_pr.id,
            source="github",
            external_id="other-finding",
            severity="medium",
            title="Unrelated finding",
            status="open",
            detected_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    db_session.flush()

    response = client.get(
        "/api/v1/analytics/projects/workspace-proj/workspace",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["project"]["project_name"] == "workspace-proj"
    assert data["project"]["total_sessions"] == 2
    assert {"Edit", "Read"}.issubset(set(data["project"]["top_tools"]))
    assert data["scorecard"]["adoption_rate"] is not None
    assert data["scorecard"]["effectiveness_score"]["score"] is not None
    assert data["scorecard"]["effectiveness_score"]["breakdown"]["success_rate"] == 0.5
    assert data["scorecard"]["effectiveness_score"]["breakdown"]["quality_outcomes"] == 1.0
    assert data["scorecard"]["effectiveness_score"]["breakdown"]["follow_through"] == 0.5
    assert data["scorecard"]["effectiveness_score"]["breakdown"]["cost_efficiency"] is not None
    assert data["scorecard"]["quality_rate"] == 1.0
    assert data["scorecard"]["measurement_confidence"] == 1.0
    assert data["repositories"][0]["repository"] == "acme/workspace"
    assert data["repositories"][0]["default_branch"] == "main"
    assert data["repositories"][0]["ai_readiness_score"] == 75.0
    assert data["enablement"]["agent_type_counts"] == {"claude_code": 1, "codex_cli": 1}
    assert set(data["enablement"]["top_models"]) == {"claude-sonnet-4", "gpt-5.3-codex"}
    assert data["friction"]["project_name"] == "workspace-proj"
    assert data["quality"]["overview"]["total_prs"] == 1
    assert data["quality"]["findings_overview"]["total_findings"] == 1
    assert data["quality"]["recent_prs"][0]["title"] == "Add project workspace"
    assert data["workflow_summary"]["fingerprinted_sessions"] == 2
    assert data["workflow_summary"]["coverage_pct"] == 1.0

    implementation = next(
        item
        for item in data["workflow_summary"]["fingerprints"]
        if item["session_type"] == "implementation"
    )
    assert implementation["steps"] == ["edit", "execute", "ship"]
    assert "context_switching" in implementation["top_friction_types"]

    debugging = next(
        item
        for item in data["workflow_summary"]["fingerprints"]
        if item["session_type"] == "debugging"
    )
    assert debugging["steps"] == ["search", "read", "execute"]
    assert debugging["success_rate"] == 0.0

    tool_error = next(
        item
        for item in data["workflow_summary"]["friction_hotspots"]
        if item["friction_type"] == "tool_error"
    )
    assert tool_error["linked_fingerprints"] == ["debugging: search -> read -> execute"]
    assert tool_error["sample_details"] == ["Tooling failed mid-session."]


def test_project_workspace_missing_project_returns_404(client, admin_headers):
    response = client.get(
        "/api/v1/analytics/projects/missing-project/workspace",
        headers=admin_headers,
    )
    assert response.status_code == 404
