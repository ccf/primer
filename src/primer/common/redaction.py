"""Secret and PII redaction for session payloads.

Pure stdlib module shared by the capture hook (client-side) and the ingest
router (server-side). Detectors are ordered: more specific patterns run
before generic ones so e.g. an Anthropic key is labeled as such rather than
matching a generic key pattern.

Replacement format is ``[REDACTED:<detector-name>]``. Detectors must never
match their own replacement tokens (idempotence is enforced by tests).
"""

import copy
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detector:
    """A named redaction pattern."""

    name: str
    pattern: re.Pattern[str]
    replacement: str | None = None  # defaults to [REDACTED:<name>]

    def apply(self, text: str) -> tuple[str, int]:
        replacement = self.replacement or f"[REDACTED:{self.name}]"
        return self.pattern.subn(replacement, text)


DETECTORS: tuple[Detector, ...] = (
    # Multiline blocks first, then specific vendor tokens, then generic shapes.
    Detector(
        "private-key-block",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.{0,65536}?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    Detector("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}")),
    Detector("openai-key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    Detector(
        "github-token",
        re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ),
    Detector("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    Detector("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    Detector(
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
    Detector("url-credentials", re.compile(r"(?<=://)[^\s/:@]+:[^\s/@]+(?=@)")),
    Detector(
        "bearer-token",
        re.compile(r"(?i)\bbearer\s+(?!\[REDACTED)[A-Za-z0-9._~+/=-]{16,}"),
    ),
    Detector(
        "env-assignment",
        re.compile(
            r"(?i)\b([A-Z0-9_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API_?KEY|ACCESS_KEY|"
            r"PRIVATE_KEY|CREDENTIALS?)[A-Z0-9_]*\s*[=:]\s*['\"]?)"
            r"(?!\[REDACTED)([^\s'\"]{8,})",
        ),
        replacement=r"\1[REDACTED:env-assignment]",
    ),
    Detector(
        "email",
        # Negative lookahead spares scp-style git remotes (git@host:org/repo.git)
        # from being mistaken for an email address in free text — a real email
        # is never immediately followed by `:<path-with-slash>`.
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b(?!:\S*/)"),
    ),
)


def redact_text(
    text: str,
    disabled: frozenset[str] = frozenset(),
    extra: tuple[Detector, ...] = (),
) -> tuple[str, dict[str, int]]:
    """Redact secrets/PII from text. Returns (redacted_text, counts_by_detector)."""
    if not text:
        return text, {}
    counts: Counter[str] = Counter()
    for detector in (*DETECTORS, *extra):
        if detector.name in disabled:
            continue
        text, n = detector.apply(text)
        if n:
            counts[detector.name] += n
    return text, dict(counts)


@lru_cache(maxsize=8)
def build_disabled_set(csv: str) -> frozenset[str]:
    """Parse a comma-separated detector-name list from config."""
    return frozenset(name.strip() for name in csv.split(",") if name.strip())


@lru_cache(maxsize=8)
def build_extra_detectors(raw_json: str) -> tuple[Detector, ...]:
    """Parse extra detectors from a JSON config string.

    Format: [{"name": "...", "pattern": "..."}]. Invalid input returns ()
    and logs a warning — bad config must never break ingestion.
    """
    if not raw_json:
        return ()
    try:
        entries = json.loads(raw_json)
        return tuple(Detector(e["name"], re.compile(e["pattern"])) for e in entries)
    except (json.JSONDecodeError, KeyError, TypeError, re.error) as exc:
        logger.warning("Ignoring invalid PRIMER_REDACTION_EXTRA_PATTERNS: %s", exc)
        return ()


_URL_USERINFO_CREDENTIALS = re.compile(r"(?i)(https?://)[^\s/@]+@")


def scrub_url_credentials(url: str) -> tuple[str, int]:
    """Remove userinfo (user:password OR token-only) from http(s) URLs.

    Removal (not tokenization) so downstream URL parsing — e.g. repository
    identity resolution from git remotes — keeps working. Only http(s) is
    scrubbed: ssh:// carries a required login (git@) that is not a secret, and
    scp-style remotes (git@host:path) have no scheme. Token-only HTTPS userinfo
    (https://<token>@host) — the most common authenticated git remote — is
    covered, where a colon-requiring rule would have leaked it.
    """
    return _URL_USERINFO_CREDENTIALS.subn(r"\1", url)


# TOP-LEVEL payload keys whose values pass through untouched. This is a DENYLIST
# over an otherwise redact-everything walk, so a new payload field is redacted by
# default — a forgotten field over-redacts (the safe direction, caught by
# analytics tests) rather than leaking (the whitelist design's silent-gap mode).
#
# Applied ONLY at the top level (see redact_ingest_dict). Nested structures —
# source_metadata, facets, tool dicts, customization details — are redacted with
# NO key exceptions, so a secret hiding under a structural-looking key name
# (e.g. details={"api_key": "sk-..."}) is still scrubbed.
#
# Two reasons a key is here:
#   1. Correctness-critical — redacting it breaks the system:
#        - api_key: the auth credential; it is sk-ant-shaped and WOULD be
#          matched by a detector, destroying authentication.
#        - git_remote_url: redacted separately via a targeted credential scrub,
#          because the full detector walk would let the email rule corrupt
#          scp-style remotes (git@host:path).
#   2. session_id: the analytics primary key, kept verbatim for cross-session
#      joins even under custom extra-patterns (a real id never matches a built-in
#      detector, so this is belt-and-suspenders / intent documentation).
_NEVER_REDACT_TOP_LEVEL_KEYS = frozenset({"api_key", "git_remote_url", "session_id"})


def _redact_value(
    value: str | None,
    counts: Counter[str],
    disabled: frozenset[str],
    extra: tuple[Detector, ...],
) -> str | None:
    if not value:
        return value
    redacted, new_counts = redact_text(value, disabled=disabled, extra=extra)
    counts.update(new_counts)
    return redacted


def _redact_tree(
    node: object,
    counts: Counter[str],
    disabled: frozenset[str],
    extra: tuple[Detector, ...],
) -> object:
    """Recursively redact every string value in a dict/list structure, with no
    key exceptions. Key-name skipping happens only at the payload top level."""
    if isinstance(node, str):
        return _redact_value(node, counts, disabled, extra)
    if isinstance(node, dict):
        return {k: _redact_tree(v, counts, disabled, extra) for k, v in node.items()}
    if isinstance(node, list):
        return [_redact_tree(item, counts, disabled, extra) for item in node]
    return node


def redact_ingest_dict(
    payload: dict,
    disabled: frozenset[str] = frozenset(),
    extra: tuple[Detector, ...] = (),
) -> tuple[dict, dict[str, int]]:
    """Redact every free-text value in a session ingest payload.

    Redact-everything-except-structural: every string value is scrubbed except
    the small ``_NEVER_REDACT_TOP_LEVEL_KEYS`` set, which is honored ONLY at the
    top level. Nested structures are redacted with no exceptions, so a secret
    under a structural-looking nested key is still caught. New payload fields are
    covered automatically. Returns a deep-copied, redacted payload and counts by
    detector; the input is never mutated.
    """
    result = copy.deepcopy(payload)
    counts: Counter[str] = Counter()

    # git_remote_url gets targeted credential removal (it is skipped by the
    # top-level walk below). The full detector walk would let the email rule
    # corrupt scp-style remotes (git@host:path).
    if result.get("git_remote_url"):
        result["git_remote_url"], n = scrub_url_credentials(result["git_remote_url"])
        if n:
            counts["url-credentials"] += n

    redacted = {
        k: (v if k in _NEVER_REDACT_TOP_LEVEL_KEYS else _redact_tree(v, counts, disabled, extra))
        for k, v in result.items()
    }
    return redacted, dict(counts)
