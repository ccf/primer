"""Backfill GitRepository readiness fields from REPO_CONFIGS in seed_demo.

The ingest service auto-creates GitRepository rows from session payloads
without readiness data. If the seed's repo-update step was skipped or
rolled back by a Postgres failover, the readiness columns end up NULL
and the maturity dashboard shows no project readiness.

Run as a one-shot: `python scripts/backfill_repo_readiness.py`
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

# Allow `from seed_demo import REPO_CONFIGS` when run from /app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_demo import REPO_CONFIGS
from sqlalchemy.orm import sessionmaker

from primer.common.database import engine
from primer.common.models import GitRepository


def main() -> int:
    factory = sessionmaker(bind=engine)
    db = factory()
    try:
        updated = 0
        for _, cfg in REPO_CONFIGS.items():
            repo = (
                db.query(GitRepository).filter(GitRepository.full_name == cfg["full_name"]).first()
            )
            if not repo:
                print(f"  (missing) {cfg['full_name']}")
                continue
            repo.primary_language = cfg["primary_language"]
            repo.language_breakdown = cfg["language_breakdown"]
            repo.repo_size_kb = cfg["repo_size_kb"]
            repo.has_claude_md = cfg["has_claude_md"]
            repo.has_agents_md = cfg["has_agents_md"]
            repo.has_claude_dir = cfg["has_claude_dir"]
            repo.ai_readiness_score = cfg["ai_readiness_score"]
            repo.ai_readiness_checked_at = datetime.utcnow() - timedelta(days=random.randint(1, 7))
            repo.has_test_harness = cfg["has_test_harness"]
            repo.has_ci_pipeline = cfg["has_ci_pipeline"]
            repo.test_maturity_score = cfg["test_maturity_score"]
            repo.repo_context_checked_at = datetime.utcnow() - timedelta(days=random.randint(1, 7))
            if not repo.default_branch:
                repo.default_branch = "main"
            updated += 1
            print(f"  {cfg['full_name']} -> readiness={cfg['ai_readiness_score']}")

        db.commit()
        print(f"Updated {updated} repos")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
