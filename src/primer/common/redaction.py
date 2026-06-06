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
from collections.abc import Iterable
from dataclasses import dataclass

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
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
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
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
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


def build_disabled_set(csv: str) -> frozenset[str]:
    """Parse a comma-separated detector-name list from config."""
    return frozenset(name.strip() for name in csv.split(",") if name.strip())


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


# Whitelist of payload locations that carry free text. Everything else
# (ids, counts, timestamps, api_key) is structural and never touched.
_TOP_LEVEL_TEXT_FIELDS = ("first_prompt", "summary")
_RECURSIVE_DICT_FIELDS = ("source_metadata", "facets")


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


def _redact_nested(
    node: object,
    counts: Counter[str],
    disabled: frozenset[str],
    extra: tuple[Detector, ...],
) -> object:
    """Recursively redact every string value in a dict/list structure."""
    if isinstance(node, str):
        return _redact_value(node, counts, disabled, extra)
    if isinstance(node, dict):
        return {k: _redact_nested(v, counts, disabled, extra) for k, v in node.items()}
    if isinstance(node, list):
        return [_redact_nested(item, counts, disabled, extra) for item in node]
    return node


def _redact_preview_items(
    items: Iterable[dict] | None,
    key: str,
    counts: Counter[str],
    disabled: frozenset[str],
    extra: tuple[Detector, ...],
) -> None:
    for item in items or ():
        if isinstance(item, dict) and item.get(key):
            item[key] = _redact_value(item[key], counts, disabled, extra)


def redact_ingest_dict(
    payload: dict,
    disabled: frozenset[str] = frozenset(),
    extra: tuple[Detector, ...] = (),
) -> tuple[dict, dict[str, int]]:
    """Redact the text-bearing fields of a session ingest payload dict.

    Returns a deep-copied, redacted payload and counts by detector. The input
    is never mutated. Only whitelisted free-text fields are touched.
    """
    result = copy.deepcopy(payload)
    counts: Counter[str] = Counter()

    for field in _TOP_LEVEL_TEXT_FIELDS:
        if result.get(field):
            result[field] = _redact_value(result[field], counts, disabled, extra)

    for message in result.get("messages") or ():
        if not isinstance(message, dict):
            continue
        if message.get("content_text"):
            message["content_text"] = _redact_value(
                message["content_text"], counts, disabled, extra
            )
        _redact_preview_items(message.get("tool_calls"), "input_preview", counts, disabled, extra)
        _redact_preview_items(
            message.get("tool_results"), "output_preview", counts, disabled, extra
        )

    for commit in result.get("commits") or ():
        if isinstance(commit, dict) and commit.get("message"):
            commit["message"] = _redact_value(commit["message"], counts, disabled, extra)

    for field in _RECURSIVE_DICT_FIELDS:
        if result.get(field):
            result[field] = _redact_nested(result[field], counts, disabled, extra)

    return result, dict(counts)
