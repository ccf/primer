"""Tests for quality metrics: ingest with commits, webhooks, GitHub sync, quality analytics."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta

from primer.common.config import settings
from primer.common.models import (
    GitRepository,
    PullRequest,
    ReviewFinding,
    SessionCommit,
)
from primer.common.models import Session as SessionModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ingest_payload(engineer_key, *, session_id=None, git_remote_url=None, commits=None):
    return {
        "session_id": session_id or str(uuid.uuid4()),
        "api_key": engineer_key,
        "project_path": "/test/test-project",
        "project_name": "test-project",
        "started_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "ended_at": datetime.utcnow().isoformat(),
        "duration_seconds": 3600,
        "message_count": 5,
        "input_tokens": 1000,
        "output_tokens": 500,
        "git_remote_url": git_remote_url,
        "commits": commits or [],
    }


# ---------------------------------------------------------------------------
# TestIngestWithCommits
# ---------------------------------------------------------------------------


class TestIngestWithCommits:
    def test_session_with_commits(self, client, engineer_with_key, admin_headers, db_session):
        _eng, key = engineer_with_key
        payload = _ingest_payload(
            key,
            commits=[
                {
                    "sha": "abc123def456",
                    "message": "fix: resolve bug",
                    "author_name": "Test",
                    "author_email": "test@test.com",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 3,
                    "lines_added": 50,
                    "lines_deleted": 10,
                },
                {
                    "sha": "def789ghi012",
                    "message": "feat: add feature",
                    "author_name": "Test",
                    "author_email": "test@test.com",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 5,
                    "lines_added": 100,
                    "lines_deleted": 20,
                },
            ],
        )
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        commits = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.session_id == payload["session_id"])
            .all()
        )
        assert len(commits) == 2
        assert {c.commit_sha for c in commits} == {"abc123def456", "def789ghi012"}
        assert commits[0].lines_added + commits[1].lines_added == 150

    def test_session_with_git_remote_creates_repo(self, client, engineer_with_key, db_session):
        _eng, key = engineer_with_key
        payload = _ingest_payload(
            key,
            git_remote_url="https://github.com/acme/widgets.git",
        )
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        repo = (
            db_session.query(GitRepository)
            .filter(GitRepository.full_name == "acme/widgets")
            .first()
        )
        assert repo is not None

        session = (
            db_session.query(SessionModel).filter(SessionModel.id == payload["session_id"]).first()
        )
        assert session.repository_id == repo.id

    def test_existing_repo_reused(self, client, engineer_with_key, db_session):
        _eng, key = engineer_with_key
        # First ingest
        p1 = _ingest_payload(key, git_remote_url="git@github.com:acme/reuse-test.git")
        client.post("/api/v1/ingest/session", json=p1)
        # Second ingest
        p2 = _ingest_payload(key, git_remote_url="https://github.com/acme/reuse-test.git")
        client.post("/api/v1/ingest/session", json=p2)

        repos = (
            db_session.query(GitRepository)
            .filter(GitRepository.full_name == "acme/reuse-test")
            .all()
        )
        assert len(repos) == 1

    def test_session_without_commits_backward_compat(self, client, engineer_with_key, db_session):
        _eng, key = engineer_with_key
        payload = _ingest_payload(key)  # no commits, no git_remote_url
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        commits = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.session_id == payload["session_id"])
            .all()
        )
        assert len(commits) == 0


# ---------------------------------------------------------------------------
# TestWebhookReceiver
# ---------------------------------------------------------------------------


class TestWebhookReceiver:
    def _sign(self, body: bytes) -> str:
        mac = hmac.new(settings.github_webhook_secret.encode(), body, hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def test_push_event_ok(self, client, db_session):
        # Set up a known repo
        repo = GitRepository(full_name="acme/push-test")
        db_session.add(repo)
        db_session.flush()

        payload = {
            "repository": {"full_name": "acme/push-test"},
            "commits": [{"id": "aaa111"}],
        }
        body = json.dumps(payload).encode()
        headers = {
            "x-github-event": "push",
            "x-hub-signature-256": self._sign(body),
            "content-type": "application/json",
        }
        resp = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        assert resp.status_code == 200

    def test_pull_request_opened(self, client, db_session):
        repo = GitRepository(full_name="acme/pr-test")
        db_session.add(repo)
        db_session.flush()

        payload = {
            "action": "opened",
            "repository": {"full_name": "acme/pr-test"},
            "pull_request": {
                "number": 42,
                "title": "Add feature X",
                "state": "open",
                "head": {"ref": "feat/x"},
                "user": {"login": "testuser"},
                "additions": 100,
                "deletions": 10,
                "changed_files": 5,
                "review_comments": 2,
                "commits": 3,
                "merged_at": None,
                "closed_at": None,
                "created_at": "2025-01-15T10:00:00Z",
            },
        }
        body = json.dumps(payload).encode()
        headers = {
            "x-github-event": "pull_request",
            "x-hub-signature-256": self._sign(body),
            "content-type": "application/json",
        }
        resp = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        assert resp.status_code == 200

        pr = db_session.query(PullRequest).filter(PullRequest.github_pr_number == 42).first()
        assert pr is not None
        assert pr.title == "Add feature X"
        assert pr.state == "open"

    def test_pr_merged_event(self, client, db_session):
        repo = GitRepository(full_name="acme/merge-test")
        db_session.add(repo)
        db_session.flush()

        # First open
        open_payload = {
            "action": "opened",
            "repository": {"full_name": "acme/merge-test"},
            "pull_request": {
                "number": 99,
                "title": "Merge me",
                "state": "open",
                "head": {"ref": "feat/merge"},
                "user": {"login": "dev"},
                "additions": 50,
                "deletions": 5,
                "changed_files": 2,
                "review_comments": 0,
                "commits": 1,
                "merged_at": None,
                "closed_at": None,
                "created_at": "2025-01-15T10:00:00Z",
            },
        }
        body = json.dumps(open_payload).encode()
        client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "x-github-event": "pull_request",
                "x-hub-signature-256": self._sign(body),
                "content-type": "application/json",
            },
        )

        # Then merge
        merge_payload = {
            "action": "closed",
            "repository": {"full_name": "acme/merge-test"},
            "pull_request": {
                "number": 99,
                "title": "Merge me",
                "state": "closed",
                "head": {"ref": "feat/merge"},
                "user": {"login": "dev"},
                "additions": 50,
                "deletions": 5,
                "changed_files": 2,
                "review_comments": 1,
                "commits": 1,
                "merged_at": "2025-01-16T12:00:00Z",
                "closed_at": "2025-01-16T12:00:00Z",
                "created_at": "2025-01-15T10:00:00Z",
            },
        }
        body = json.dumps(merge_payload).encode()
        resp = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "x-github-event": "pull_request",
                "x-hub-signature-256": self._sign(body),
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 200

        pr = db_session.query(PullRequest).filter(PullRequest.github_pr_number == 99).first()
        assert pr.state == "merged"
        assert pr.merged_at is not None

    def test_invalid_signature_rejected(self, client):
        payload = {"repository": {"full_name": "acme/bad"}, "commits": []}
        body = json.dumps(payload).encode()
        headers = {
            "x-github-event": "push",
            "x-hub-signature-256": "sha256=invalid",
            "content-type": "application/json",
        }
        resp = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        # Only rejected if webhook_secret is configured
        if settings.github_webhook_secret:
            assert resp.status_code == 401
        else:
            assert resp.status_code == 200

    def test_unknown_event_noop(self, client):
        payload = {}
        body = json.dumps(payload).encode()
        headers = {
            "x-github-event": "star",
            "x-hub-signature-256": self._sign(body),
            "content-type": "application/json",
        }
        resp = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestGitHubSync
# ---------------------------------------------------------------------------


class TestGitHubSync:
    def test_sync_requires_admin(self, client, engineer_with_key):
        _eng, key = engineer_with_key
        resp = client.post(
            "/api/v1/analytics/github/sync",
            headers={"x-api-key": key},
        )
        assert resp.status_code == 403

    def test_status_returns_not_configured(self, client, admin_headers, db_session, monkeypatch):
        monkeypatch.setattr("primer.server.services.github_service.settings.github_app_id", None)
        resp = client.get("/api/v1/analytics/github/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["repos_count"] >= 0


# ---------------------------------------------------------------------------
# TestQualityMetrics
# ---------------------------------------------------------------------------


class TestQualityMetrics:
    def test_empty_state(self, client, admin_headers):
        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overview"]["total_commits"] == 0
        assert data["daily_volume"] == []
        assert data["sessions_analyzed"] == 0

    def test_sessions_with_commits(self, client, engineer_with_key, admin_headers, db_session):
        _eng, key = engineer_with_key
        now = datetime.utcnow()

        # Ingest a session with commits
        payload = _ingest_payload(
            key,
            git_remote_url="https://github.com/acme/quality-test.git",
            commits=[
                {
                    "sha": "qm_commit_1",
                    "message": "fix: stuff",
                    "author_name": "Test",
                    "author_email": "t@t.com",
                    "committed_at": now.isoformat(),
                    "files_changed": 2,
                    "lines_added": 30,
                    "lines_deleted": 5,
                },
                {
                    "sha": "qm_commit_2",
                    "message": "feat: new",
                    "author_name": "Test",
                    "author_email": "t@t.com",
                    "committed_at": now.isoformat(),
                    "files_changed": 4,
                    "lines_added": 80,
                    "lines_deleted": 15,
                },
            ],
        )
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overview"]["total_commits"] >= 2
        assert data["overview"]["total_lines_added"] >= 110
        assert data["overview"]["sessions_with_commits"] >= 1

    def test_daily_volume_aggregation(self, client, engineer_with_key, admin_headers, db_session):
        _eng, key = engineer_with_key
        now = datetime.utcnow()

        payload = _ingest_payload(
            key,
            commits=[
                {
                    "sha": "dv_commit_1",
                    "message": "daily vol test",
                    "committed_at": now.isoformat(),
                    "files_changed": 1,
                    "lines_added": 10,
                    "lines_deleted": 2,
                },
            ],
        )
        client.post("/api/v1/ingest/session", json=payload)

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        data = resp.json()
        # Should have at least one daily entry
        assert len(data["daily_volume"]) >= 1

    def test_engineer_quality(self, client, engineer_with_key, admin_headers, db_session):
        eng, key = engineer_with_key

        payload = _ingest_payload(
            key,
            commits=[
                {
                    "sha": "eq_commit_1",
                    "message": "eng quality test",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 1,
                    "lines_added": 25,
                    "lines_deleted": 3,
                },
            ],
        )
        client.post("/api/v1/ingest/session", json=payload)

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        data = resp.json()
        engineers = data["engineer_quality"]
        assert len(engineers) >= 1
        assert any(e["engineer_id"] == eng.id for e in engineers)

    def test_engineer_quality_treats_null_review_comments_as_zero(
        self, client, engineer_with_key, admin_headers, db_session
    ):
        eng, key = engineer_with_key

        payload = _ingest_payload(
            key,
            session_id="eq-null-comments",
            git_remote_url="https://github.com/acme/null-comments.git",
            commits=[
                {
                    "sha": "eq_null_comments_commit",
                    "message": "eng quality null comments test",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 1,
                    "lines_added": 25,
                    "lines_deleted": 3,
                },
            ],
        )
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        repo = (
            db_session.query(GitRepository)
            .filter(GitRepository.full_name == "acme/null-comments")
            .one()
        )
        pr = PullRequest(
            repository_id=repo.id,
            engineer_id=eng.id,
            github_pr_number=303,
            title="Null comment count PR",
            state="merged",
            review_comments_count=None,
            pr_created_at=datetime.utcnow() - timedelta(hours=4),
            merged_at=datetime.utcnow() - timedelta(hours=1),
        )
        db_session.add(pr)
        db_session.flush()

        commit = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.commit_sha == "eq_null_comments_commit")
            .one()
        )
        commit.pull_request_id = pr.id
        db_session.flush()

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        engineer_row = next(row for row in data["engineer_quality"] if row["engineer_id"] == eng.id)
        assert engineer_row["avg_review_comments"] == 0.0

    def test_quality_by_session_type(self, client, engineer_with_key, admin_headers, db_session):
        _eng, key = engineer_with_key

        payload = _ingest_payload(
            key,
            commits=[
                {
                    "sha": "qt_commit_1",
                    "message": "type test",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 1,
                    "lines_added": 15,
                    "lines_deleted": 1,
                },
            ],
        )
        # Add facets with session_type
        payload["facets"] = {
            "session_type": "bug_fix",
            "outcome": "success",
        }
        client.post("/api/v1/ingest/session", json=payload)

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        data = resp.json()
        types = data["by_session_type"]
        assert len(types) >= 1

    def test_auth_required(self, client):
        resp = client.get("/api/v1/analytics/quality-metrics")
        assert resp.status_code == 401

    def test_quality_attribution_links_session_behaviors_to_pr_outcomes(
        self, client, engineer_with_key, admin_headers, db_session
    ):
        _eng, key = engineer_with_key
        now = datetime.utcnow()

        payload = _ingest_payload(
            key,
            session_id="attrib-session-a",
            git_remote_url="https://github.com/acme/attrib-test.git",
            commits=[
                {
                    "sha": "attrib_commit_a",
                    "message": "fix: attributed change",
                    "committed_at": now.isoformat(),
                    "files_changed": 2,
                    "lines_added": 20,
                    "lines_deleted": 5,
                },
            ],
        )
        payload["permission_mode"] = "on-request"
        payload["tool_usages"] = [
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 1},
        ]
        payload["facets"] = {"session_type": "bug_fix", "outcome": "success"}
        resp = client.post("/api/v1/ingest/session", json=payload)
        assert resp.status_code == 200

        payload_b = _ingest_payload(
            key,
            session_id="attrib-session-b",
            commits=[
                {
                    "sha": "attrib_commit_b",
                    "message": "feat: attributed change",
                    "committed_at": now.isoformat(),
                    "files_changed": 1,
                    "lines_added": 8,
                    "lines_deleted": 3,
                },
            ],
        )
        payload_b["agent_type"] = "codex_cli"
        payload_b["permission_mode"] = "never"
        payload_b["facets"] = {"session_type": "feature_delivery", "outcome": "failure"}
        resp = client.post("/api/v1/ingest/session", json=payload_b)
        assert resp.status_code == 200

        repo = (
            db_session.query(GitRepository)
            .filter(GitRepository.full_name == "acme/attrib-test")
            .first()
        )
        assert repo is not None

        pr_merged = PullRequest(
            repository_id=repo.id,
            github_pr_number=101,
            title="Merged attribution PR",
            state="merged",
            review_comments_count=2,
            pr_created_at=now - timedelta(hours=5),
            merged_at=now - timedelta(hours=1),
        )
        pr_closed = PullRequest(
            repository_id=repo.id,
            github_pr_number=102,
            title="Closed attribution PR",
            state="closed",
            review_comments_count=4,
            pr_created_at=now - timedelta(hours=6),
            closed_at=now - timedelta(hours=2),
        )
        db_session.add_all([pr_merged, pr_closed])
        db_session.flush()

        commit_a = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.commit_sha == "attrib_commit_a")
            .first()
        )
        commit_b = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.commit_sha == "attrib_commit_b")
            .first()
        )
        commit_a.pull_request_id = pr_merged.id
        commit_b.pull_request_id = pr_closed.id

        db_session.add_all(
            [
                ReviewFinding(
                    pull_request_id=pr_merged.id,
                    source="bugbot",
                    external_id="attrib-finding-1",
                    severity="high",
                    title="High issue",
                    status="fixed",
                    detected_at=now - timedelta(hours=4),
                ),
                ReviewFinding(
                    pull_request_id=pr_merged.id,
                    source="bugbot",
                    external_id="attrib-finding-2",
                    severity="medium",
                    title="Medium issue",
                    status="open",
                    detected_at=now - timedelta(hours=4),
                ),
            ]
        )
        db_session.flush()

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        def _row(dimension, label):
            return next(
                row
                for row in data["attribution"]
                if row["dimension"] == dimension and row["label"] == label
            )

        bug_fix = _row("session_type", "bug_fix")
        assert bug_fix["linked_sessions"] == 1
        assert bug_fix["linked_prs"] == 1
        assert bug_fix["merge_rate"] == 1.0
        assert bug_fix["avg_findings_per_pr"] == 2.0
        assert bug_fix["high_severity_findings_per_pr"] == 1.0
        assert bug_fix["findings_fix_rate"] == 0.5

        codex = _row("agent_type", "codex_cli")
        assert codex["linked_prs"] == 1
        assert codex["merge_rate"] == 0.0

        no_tools = _row("tool_breadth", "No tools")
        assert no_tools["linked_sessions"] == 1
        assert no_tools["linked_prs"] == 1

        on_request = _row("permission_mode", "on-request")
        assert on_request["avg_review_comments_per_pr"] == 2.0

        debugging = _row("workflow_archetype", "debugging")
        assert debugging["linked_sessions"] == 1
        assert debugging["linked_prs"] == 1
        assert debugging["merge_rate"] == 1.0

        bug_fix_fingerprint = _row("workflow_fingerprint", "bug fix: read -> edit -> ship")
        assert bug_fix_fingerprint["linked_sessions"] == 1
        assert bug_fix_fingerprint["linked_prs"] == 1
        assert bug_fix_fingerprint["avg_findings_per_pr"] == 2.0


# ---------------------------------------------------------------------------
# TestCommitPRCorrelation
# ---------------------------------------------------------------------------


class TestCommitPRCorrelation:
    def test_commit_linked_to_pr(self, client, engineer_with_key, db_session):
        _eng, key = engineer_with_key

        # Create a repo and PR
        repo = GitRepository(full_name="acme/corr-test")
        db_session.add(repo)
        db_session.flush()

        pr = PullRequest(
            repository_id=repo.id,
            github_pr_number=10,
            state="merged",
            title="Test PR",
        )
        db_session.add(pr)
        db_session.flush()

        # Ingest a session with a commit whose SHA we'll link
        payload = _ingest_payload(
            key,
            git_remote_url="https://github.com/acme/corr-test.git",
            commits=[
                {
                    "sha": "linked_sha_001",
                    "message": "linked commit",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 1,
                    "lines_added": 5,
                    "lines_deleted": 0,
                },
            ],
        )
        client.post("/api/v1/ingest/session", json=payload)

        # Manually link the commit to the PR (simulating what sync_repository does)
        sc = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.commit_sha == "linked_sha_001")
            .first()
        )
        assert sc is not None
        sc.pull_request_id = pr.id
        db_session.flush()

        assert sc.pull_request_id == pr.id

    def test_unmatched_commit_has_no_pr(self, client, engineer_with_key, db_session):
        _eng, key = engineer_with_key

        payload = _ingest_payload(
            key,
            commits=[
                {
                    "sha": "unmatched_sha_001",
                    "message": "unmatched",
                    "committed_at": datetime.utcnow().isoformat(),
                    "files_changed": 1,
                    "lines_added": 3,
                    "lines_deleted": 0,
                },
            ],
        )
        client.post("/api/v1/ingest/session", json=payload)

        sc = (
            db_session.query(SessionCommit)
            .filter(SessionCommit.commit_sha == "unmatched_sha_001")
            .first()
        )
        assert sc is not None
        assert sc.pull_request_id is None

    def test_pr_linked_to_engineer_via_github_username(self, client, engineer_with_key, db_session):
        eng, _key = engineer_with_key
        eng.github_username = "ghuser123"
        db_session.flush()

        repo = GitRepository(full_name="acme/eng-link-test")
        db_session.add(repo)
        db_session.flush()

        # Simulate webhook creating a PR with matching author
        pr_payload = {
            "action": "opened",
            "repository": {"full_name": "acme/eng-link-test"},
            "pull_request": {
                "number": 77,
                "title": "Engineer link test",
                "state": "open",
                "head": {"ref": "feat/test"},
                "user": {"login": "ghuser123"},
                "additions": 10,
                "deletions": 0,
                "changed_files": 1,
                "review_comments": 0,
                "commits": 1,
                "merged_at": None,
                "closed_at": None,
                "created_at": "2025-06-01T10:00:00Z",
            },
        }
        body = json.dumps(pr_payload).encode()
        mac = hmac.new(settings.github_webhook_secret.encode(), body, hashlib.sha256)
        sig = f"sha256={mac.hexdigest()}"
        client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "x-github-event": "pull_request",
                "x-hub-signature-256": sig,
                "content-type": "application/json",
            },
        )

        pr = db_session.query(PullRequest).filter(PullRequest.github_pr_number == 77).first()
        assert pr is not None
        assert pr.engineer_id == eng.id
