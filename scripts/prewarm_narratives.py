"""Pre-generate narrative insights for the demo so visitors get cached output.

Run after seeding. Hits org, every team, and every engineer scope so the
NarrativeCache table is populated and the live Anthropic API isn't called
during demo browsing.
"""

from __future__ import annotations

import sys

from sqlalchemy.orm import sessionmaker

from primer.common.config import settings
from primer.common.database import engine
from primer.common.models import Engineer, Team
from primer.server.services.narrative_service import generate_narrative


def main() -> int:
    if not getattr(settings, "anthropic_api_key", None):
        print("PRIMER_ANTHROPIC_API_KEY not set; skipping narrative prewarm.")
        return 0

    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    try:
        scopes: list[tuple[str, str | None, str | None]] = [("org", None, None)]
        scopes.extend(("team", t.id, None) for t in db.query(Team).all())
        scopes.extend(("engineer", None, e.id) for e in db.query(Engineer).all())

        ok = 0
        failed = 0
        for scope, team_id, engineer_id in scopes:
            label = team_id or engineer_id or "org"
            try:
                generate_narrative(
                    db,
                    scope=scope,
                    team_id=team_id,
                    engineer_id=engineer_id,
                )
                ok += 1
                print(f"  prewarmed {scope} {label}")
            except Exception as e:
                failed += 1
                print(f"  failed {scope} {label}: {e}")

        print(f"Prewarm complete: {ok} ok, {failed} failed")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
