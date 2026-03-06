"""Tests for automated review findings: BugBot parser, upsert, analytics, API."""

import uuid
from datetime import datetime, timedelta

from primer.common.models import (
    GitRepository,
    PullRequest,
    ReviewFinding,
)
from primer.server.services.review_finding_service import (
    parse_bugbot_comment,
    parse_comments,
    upsert_findings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(db):
    repo = GitRepository(full_name="test-org/test-repo")
    db.add(repo)
    db.flush()
    return repo


def _make_pr(db, repo, *, engineer_id=None, pr_number=1):
    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=pr_number,
        state="open",
        engineer_id=engineer_id,
        pr_created_at=datetime.utcnow(),
    )
    db.add(pr)
    db.flush()
    return pr


def _bugbot_comment(
    *,
    title="Null pointer dereference",
    severity="High",
    description="The variable may be None",
    bug_id=None,
    file_path="src/app.py",
    line_start=10,
    line_end=20,
    created_at=None,
):
    bug_id = bug_id or str(uuid.uuid4())
    created_at = created_at or datetime.utcnow().isoformat() + "Z"
    return {
        "body": (
            f"### {title}\n\n"
            f"**{severity} Severity**\n\n"
            f"<!-- DESCRIPTION START -->\n{description}\n<!-- DESCRIPTION END -->\n\n"
            f"<!-- BUGBOT_BUG_ID: {bug_id} -->\n\n"
            f"<!-- LOCATIONS START\n{file_path}#L{line_start}-L{line_end}\nLOCATIONS END -->"
        ),
        "created_at": created_at,
    }


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestBugBotParser:
    def test_parse_valid_comment(self):
        comment = _bugbot_comment(
            title="Buffer overflow risk",
            severity="High",
            description="Unsafe memory access detected",
            bug_id="abc-123",
            file_path="src/core.py",
            line_start=42,
            line_end=50,
        )
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.source == "bugbot"
        assert finding.external_id == "abc-123"
        assert finding.severity == "high"
        assert finding.title == "Buffer overflow risk"
        assert finding.description == "Unsafe memory access detected"
        assert finding.file_path == "src/core.py"
        assert finding.line_number == 42
        assert finding.pull_request_id == "pr-id-1"
        assert finding.status == "open"

    def test_parse_medium_severity(self):
        comment = _bugbot_comment(severity="Medium")
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.severity == "medium"

    def test_parse_low_severity(self):
        comment = _bugbot_comment(severity="Low")
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.severity == "low"

    def test_parse_non_bugbot_comment_returns_none(self):
        comment = {"body": "Great PR, LGTM!", "created_at": "2026-01-01T00:00:00Z"}
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is None

    def test_parse_empty_body_returns_none(self):
        comment = {"body": "", "created_at": "2026-01-01T00:00:00Z"}
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is None

    def test_parse_no_body_returns_none(self):
        comment = {"created_at": "2026-01-01T00:00:00Z"}
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is None

    def test_parse_location_without_line_numbers(self):
        comment = {
            "body": (
                "### Title\n\n**High Severity**\n\n"
                "<!-- DESCRIPTION START -->\nDesc\n<!-- DESCRIPTION END -->\n\n"
                "<!-- BUGBOT_BUG_ID: xyz -->\n\n"
                "<!-- LOCATIONS START\nsrc/file.py\nLOCATIONS END -->"
            ),
            "created_at": "2026-01-01T00:00:00Z",
        }
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.file_path == "src/file.py"
        assert finding.line_number is None

    def test_parse_no_locations_block(self):
        comment = {
            "body": (
                "### Title\n\n**High Severity**\n\n"
                "<!-- DESCRIPTION START -->\nDesc\n<!-- DESCRIPTION END -->\n\n"
                "<!-- BUGBOT_BUG_ID: no-loc -->"
            ),
            "created_at": "2026-01-01T00:00:00Z",
        }
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.file_path is None
        assert finding.line_number is None

    def test_parse_no_description_block(self):
        comment = {
            "body": ("### Title\n\n**High Severity**\n\n<!-- BUGBOT_BUG_ID: no-desc -->"),
            "created_at": "2026-01-01T00:00:00Z",
        }
        finding = parse_bugbot_comment(comment, "pr-id-1")
        assert finding is not None
        assert finding.description is None


class TestParseComments:
    def test_multiple_comments_mixed(self):
        comments = [
            _bugbot_comment(bug_id="bug-1"),
            {"body": "LGTM"},
            _bugbot_comment(bug_id="bug-2"),
        ]
        findings = parse_comments(comments, "pr-id-1")
        assert len(findings) == 2
        ids = {f.external_id for f in findings}
        assert ids == {"bug-1", "bug-2"}


# ---------------------------------------------------------------------------
# Upsert tests
# ---------------------------------------------------------------------------


class TestUpsertFindings:
    def test_insert_new_findings(self, db_session):
        repo = _make_repo(db_session)
        pr = _make_pr(db_session, repo)

        findings = parse_comments(
            [_bugbot_comment(bug_id="new-1"), _bugbot_comment(bug_id="new-2")],
            pr.id,
        )
        inserted = upsert_findings(db_session, findings)
        assert inserted == 2

        stored = (
            db_session.query(ReviewFinding).filter(ReviewFinding.pull_request_id == pr.id).all()
        )
        assert len(stored) == 2

    def test_duplicate_finding_not_inserted(self, db_session):
        repo = _make_repo(db_session)
        pr = _make_pr(db_session, repo)

        findings1 = parse_comments([_bugbot_comment(bug_id="dup-1")], pr.id)
        upsert_findings(db_session, findings1)

        # Try inserting the same external_id again
        findings2 = parse_comments([_bugbot_comment(bug_id="dup-1")], pr.id)
        inserted = upsert_findings(db_session, findings2)
        assert inserted == 0

        stored = (
            db_session.query(ReviewFinding)
            .filter(
                ReviewFinding.pull_request_id == pr.id,
                ReviewFinding.external_id == "dup-1",
            )
            .all()
        )
        assert len(stored) == 1


# ---------------------------------------------------------------------------
# Quality service findings aggregation
# ---------------------------------------------------------------------------


class TestFindingsAggregation:
    def test_findings_overview_in_quality_metrics(
        self, db_session, client, engineer_with_key, admin_headers
    ):
        eng, _key = engineer_with_key
        repo = _make_repo(db_session)
        pr = _make_pr(db_session, repo, engineer_id=eng.id)

        # Insert some findings
        now = datetime.utcnow()
        findings = [
            ReviewFinding(
                pull_request_id=pr.id,
                source="bugbot",
                external_id="agg-1",
                severity="high",
                title="Bug 1",
                status="fixed",
                detected_at=now - timedelta(days=1),
            ),
            ReviewFinding(
                pull_request_id=pr.id,
                source="bugbot",
                external_id="agg-2",
                severity="medium",
                title="Bug 2",
                status="open",
                detected_at=now,
            ),
        ]
        for f in findings:
            db_session.add(f)
        db_session.flush()

        resp = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        fo = data.get("findings_overview")
        assert fo is not None
        assert fo["total_findings"] == 2
        assert fo["by_severity"]["high"] == 1
        assert fo["by_severity"]["medium"] == 1
        assert fo["fix_rate"] == 0.5


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestReviewFindingsEndpoint:
    def test_list_findings(self, db_session, client, engineer_with_key, admin_headers):
        eng, _key = engineer_with_key
        repo = _make_repo(db_session)
        pr = _make_pr(db_session, repo, engineer_id=eng.id)

        finding = ReviewFinding(
            pull_request_id=pr.id,
            source="bugbot",
            external_id="api-1",
            severity="high",
            title="API test bug",
            status="open",
            detected_at=datetime.utcnow(),
        )
        db_session.add(finding)
        db_session.flush()

        resp = client.get("/api/v1/analytics/review-findings", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 1
        items = data["items"]
        # Check the response includes PR and repo info
        item = next((i for i in items if i["title"] == "API test bug"), None)
        assert item is not None
        assert item["pr_number"] == pr.github_pr_number
        assert item["repository"] == repo.full_name

    def test_filter_by_severity(self, db_session, client, engineer_with_key, admin_headers):
        eng, _key = engineer_with_key
        repo = _make_repo(db_session)
        pr = _make_pr(db_session, repo, engineer_id=eng.id, pr_number=99)

        for sev in ["high", "low"]:
            db_session.add(
                ReviewFinding(
                    pull_request_id=pr.id,
                    source="bugbot",
                    external_id=f"filter-{sev}",
                    severity=sev,
                    title=f"{sev} bug",
                    status="open",
                    detected_at=datetime.utcnow(),
                )
            )
        db_session.flush()

        resp = client.get("/api/v1/analytics/review-findings?severity=high", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["severity"] == "high" for i in items)

    def test_filter_by_source(self, db_session, client, engineer_with_key, admin_headers):
        resp = client.get("/api/v1/analytics/review-findings?source=bugbot", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["source"] == "bugbot" for i in items)
