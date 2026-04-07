"""Backfill data linkages for the demo so dashboards aren't sparse.

Fixes two issues that surface when seeding ran racy/partial:

1. Sessions with project_name but no repository_id -> link them via repo_map
   so maturity_service can compute project readiness.

2. All PRs end up "Claude-assisted" because seed only creates PRs from
   sessions with commits. To make the Claude PR comparison meaningful,
   detach SessionCommits from ~35% of PRs so they show up in the
   non-Claude bucket.
"""

from __future__ import annotations

import random
import sys

from sqlalchemy.orm import sessionmaker

from primer.common.database import engine
from primer.common.models import GitRepository, PullRequest, SessionCommit
from primer.common.models import Session as SessionModel


def _backfill_pull_requests(db) -> int:
    """If no PRs exist, run seed_demo's seed_pull_requests against current data."""
    from primer.common.models import GitRepository as Repo
    from primer.common.models import PullRequest

    if db.query(PullRequest).count() > 0:
        return 0

    # Build repo_map keyed the way seed_demo expects (short project_name)
    repo_map: dict[str, str] = {}
    for repo in db.query(Repo).all():
        short = repo.full_name.split("/")[-1]
        repo_map[short] = repo.id

    # Import here so this script doesn't fail when run on a fresh DB
    from scripts.seed_demo import seed_pull_requests, seed_review_findings

    pr_map = seed_pull_requests(db, repo_map)
    seed_review_findings(db, pr_map)
    return len(pr_map)


def main() -> int:
    factory = sessionmaker(bind=engine)
    db = factory()

    try:
        # ── 1. Link sessions to repositories ────────────────────────────
        repos = db.query(GitRepository).all()
        # Map both short name (everything after the last `/`) and full_name
        repo_by_name: dict[str, str] = {}
        for r in repos:
            repo_by_name[r.full_name] = r.id
            short = r.full_name.split("/")[-1]
            repo_by_name[short] = r.id

        unlinked = (
            db.query(SessionModel)
            .filter(
                SessionModel.repository_id.is_(None),
                SessionModel.project_name.isnot(None),
            )
            .all()
        )
        linked = 0
        for s in unlinked:
            repo_id = repo_by_name.get(s.project_name)
            if repo_id:
                s.repository_id = repo_id
                linked += 1
        db.commit()
        print(f"Linked {linked}/{len(unlinked)} unlinked sessions to repositories")

        # ── 2. Backfill PRs if missing ──────────────────────────────────
        created_prs = _backfill_pull_requests(db)
        if created_prs:
            print(f"Backfilled {created_prs} pull requests from existing commits")

        # ── 3. Detach a fraction of PRs from sessions to populate non-Claude ──
        all_pr_ids = [row[0] for row in db.query(PullRequest.id).all()]
        if not all_pr_ids:
            print("No PRs found; skipping non-claude split.")
            return 0

        # Find PRs currently linked to a session via SessionCommit
        linked_pr_ids = sorted(
            {
                row[0]
                for row in db.query(SessionCommit.pull_request_id)
                .filter(SessionCommit.pull_request_id.isnot(None))
                .all()
            }
        )

        if not linked_pr_ids:
            print("No PRs linked to sessions; nothing to detach.")
            return 0

        random.seed(42)
        target_non_claude = int(len(all_pr_ids) * 0.35)
        to_detach = random.sample(linked_pr_ids, min(target_non_claude, len(linked_pr_ids)))

        detached = (
            db.query(SessionCommit)
            .filter(SessionCommit.pull_request_id.in_(to_detach))
            .update({SessionCommit.pull_request_id: None}, synchronize_session=False)
        )
        db.commit()
        print(
            f"Detached {detached} SessionCommit rows across {len(to_detach)} PRs "
            f"(now non-Claude); {len(linked_pr_ids) - len(to_detach)} PRs remain Claude-assisted"
        )

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
