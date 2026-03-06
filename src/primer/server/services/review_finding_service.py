"""Review finding parser registry and analytics."""

import logging
import re
import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from primer.common.models import ReviewFinding
from primer.common.utils import parse_github_datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------

FindingParser = Callable[[dict, str], ReviewFinding | None]

PARSERS: dict[str, FindingParser] = {}


def register_parser(source: str):
    """Decorator to register a finding parser for a given source."""

    def decorator(fn: FindingParser) -> FindingParser:
        PARSERS[source] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# BugBot parser
# ---------------------------------------------------------------------------

_BUGBOT_BUG_ID_RE = re.compile(r"<!--\s*BUGBOT_BUG_ID:\s*(\S+)\s*-->")
_BUGBOT_SEVERITY_RE = re.compile(r"\*\*(High|Medium|Low|Info)\s+Severity\*\*", re.IGNORECASE)
_BUGBOT_TITLE_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_BUGBOT_DESC_RE = re.compile(
    r"<!--\s*DESCRIPTION START\s*-->\s*(.*?)\s*<!--\s*DESCRIPTION END\s*-->",
    re.DOTALL,
)
_BUGBOT_LOCATIONS_RE = re.compile(
    r"<!--\s*LOCATIONS START\s*\n(.*?)\nLOCATIONS END\s*-->",
    re.DOTALL,
)


@register_parser("bugbot")
def parse_bugbot_comment(comment: dict, pull_request_id: str) -> ReviewFinding | None:
    """Parse a cursor[bot] / BugBot PR comment into a ReviewFinding."""
    body = comment.get("body", "")
    if not body:
        return None

    bug_id_match = _BUGBOT_BUG_ID_RE.search(body)
    if not bug_id_match:
        return None

    external_id = bug_id_match.group(1)

    # Title: first ### heading
    title_match = _BUGBOT_TITLE_RE.search(body)
    title = title_match.group(1).strip() if title_match else "Untitled finding"

    # Severity
    severity_match = _BUGBOT_SEVERITY_RE.search(body)
    severity = severity_match.group(1).lower() if severity_match else "medium"

    # Description
    desc_match = _BUGBOT_DESC_RE.search(body)
    description = desc_match.group(1).strip() if desc_match else None

    # File path + line number from LOCATIONS block
    file_path = None
    line_number = None
    locations_match = _BUGBOT_LOCATIONS_RE.search(body)
    if locations_match:
        first_loc = locations_match.group(1).strip().split("\n")[0].strip()
        if "#L" in first_loc:
            parts = first_loc.split("#L", 1)
            file_path = parts[0]
            line_range = parts[1]
            # e.g. "10-20" or "10"
            line_number = int(line_range.split("-")[0]) if line_range else None
        elif first_loc:
            file_path = first_loc

    detected_at = parse_github_datetime(comment.get("created_at")) or datetime.utcnow()

    return ReviewFinding(
        id=str(uuid.uuid4()),
        pull_request_id=pull_request_id,
        source="bugbot",
        external_id=external_id,
        severity=severity,
        title=title[:500],
        description=description,
        file_path=file_path,
        line_number=line_number,
        status="open",
        detected_at=detected_at,
    )


# ---------------------------------------------------------------------------
# Upsert / sync helpers
# ---------------------------------------------------------------------------


def parse_comments(comments: list[dict], pull_request_id: str) -> list[ReviewFinding]:
    """Run all registered parsers over a list of comments, returning new findings."""
    findings: list[ReviewFinding] = []
    for comment in comments:
        for parser in PARSERS.values():
            finding = parser(comment, pull_request_id)
            if finding:
                findings.append(finding)
    return findings


def upsert_findings(db: Session, findings: list[ReviewFinding]) -> int:
    """Insert findings, skipping duplicates (same pull_request_id + external_id)."""
    inserted = 0
    for finding in findings:
        try:
            with db.begin_nested():
                db.add(finding)
            inserted += 1
        except IntegrityError:
            pass  # Duplicate — already exists
    db.flush()
    return inserted
