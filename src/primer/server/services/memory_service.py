"""Memory store service layer: scopes, sketches, dedup, flood control.

Plan 2a of the hive-mind memory spec
(docs/superpowers/specs/2026-05-18-hive-mind-memory-design.md §4-§5).
The write path persists quarantined `sketch` entries only; promotion to
`active` is the consolidation engine's job (Plan 2b).
"""

import logging

from primer.common.config import settings

logger = logging.getLogger(__name__)


def memory_capture_active() -> bool:
    """Memory capture is gated on the redaction pipeline (spec §16 #1).

    Sketches persist transcript-derived text, so no sketch is ever written
    while redaction is disabled — there is no unredacted capture mode.
    """
    return settings.memory_enabled and settings.redaction_enabled
