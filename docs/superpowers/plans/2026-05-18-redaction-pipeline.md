# Redaction Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the P0 secret/PII redaction pipeline that scrubs sensitive content from session payloads at the capture layer (hook, client-side) and at the server ingest chokepoint (router, before any persistence — including the `background_jobs` table).

**Architecture:** A pure, dependency-free detector module (`src/primer/common/redaction.py`) holds named regex detectors and a whitelist payload walker that redacts only known text-bearing fields of `SessionIngestPayload`. It is wired into two places: `session_end.py` (hook; before POST, env-controlled) and `routers/ingest.py` (server; immediately after auth, before the async path serializes the payload into the `background_jobs` table — covering single, bulk, sync, and async paths with one chokepoint). This is prerequisite #1 in `docs/superpowers/specs/2026-05-18-hive-mind-memory-design.md` §16, and a standalone P0 roadmap item.

**Tech Stack:** Python 3.12 stdlib (`re`, `dataclasses`, `collections.Counter`), pydantic-settings config (`PRIMER_` prefix), pytest with existing `client` / `db_session` / `engineer_with_key` fixtures.

**Context for the implementer (read these first):**
- `src/primer/common/redaction.py` does not exist yet — you create it.
- Hook payload construction: `src/primer/hook/session_end.py:134` (`payload = meta.to_ingest_payload(...)`), POST at line 137.
- Server ingest: `src/primer/server/routers/ingest.py` — `ingest_session` (line ~49) has an **async path** that serializes the payload into the `background_jobs` table (line ~66 `serialized = payload.model_dump(...)`) and a **sync fallback**; `ingest_bulk` is at line ~130. Redaction must run **before** the async serialization, or secrets persist in the jobs table.
- Text-bearing payload fields (verified against `SessionIngestPayload` in `src/primer/common/schemas.py:441` and `to_ingest_payload` in `src/primer/hook/extractor.py:76`): `first_prompt`, `summary`, `messages[].content_text`, `messages[].tool_calls[].input_preview`, `messages[].tool_results[].output_preview`, `commits[].message`, and all nested string values inside `source_metadata` and `facets`. **Never** touch `api_key` (needed for auth) or structural fields.
- Conventions: line length 100 (ruff), `str | None` unions, tests use SQLite via `tests/conftest.py` fixtures; `_disable_background_jobs_in_tests` is autouse — re-enable per-test with `monkeypatch.setattr(settings, "background_jobs_enabled", True)` when testing the async path.

---

### Task 1: Detector engine with the first detector (Anthropic API key)

**Files:**
- Create: `src/primer/common/redaction.py`
- Create: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_redaction.py
"""Tests for the secret/PII redaction pipeline."""

from primer.common.redaction import redact_text


def test_redacts_anthropic_api_key():
    text = "export ANTHROPIC_API_KEY and key is sk-ant-api03-AbCdEf123456789012345 ok"
    redacted, counts = redact_text(text)
    assert "sk-ant-" not in redacted
    assert "[REDACTED:anthropic-key]" in redacted
    assert counts["anthropic-key"] == 1


def test_clean_text_unchanged():
    text = "Refactored the analytics service and added tests."
    redacted, counts = redact_text(text)
    assert redacted == text
    assert sum(counts.values()) == 0


def test_none_and_empty_are_safe():
    assert redact_text("") == ("", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ccf/git/primer && pytest tests/test_redaction.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'primer.common.redaction'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/primer/common/redaction.py
"""Secret and PII redaction for session payloads.

Pure stdlib module shared by the capture hook (client-side) and the ingest
router (server-side). Detectors are ordered: more specific patterns run
before generic ones so e.g. an Anthropic key is labeled as such rather than
matching a generic key pattern.

Replacement format is ``[REDACTED:<detector-name>]``. Detectors must never
match their own replacement tokens (idempotence is enforced by tests).
"""

import re
from collections import Counter
from dataclasses import dataclass


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
    Detector("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}")),
)


def redact_text(
    text: str, disabled: frozenset[str] = frozenset()
) -> tuple[str, dict[str, int]]:
    """Redact secrets/PII from text. Returns (redacted_text, counts_by_detector)."""
    if not text:
        return text, {}
    counts: Counter[str] = Counter()
    for detector in DETECTORS:
        if detector.name in disabled:
            continue
        text, n = detector.apply(text)
        if n:
            counts[detector.name] += n
    return text, dict(counts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_redaction.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/primer/common/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detector engine with anthropic-key detector"
```

---

### Task 2: Full secret detector set

**Files:**
- Modify: `src/primer/common/redaction.py` (extend `DETECTORS`)
- Modify: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing golden-table test**

```python
# append to tests/test_redaction.py
import pytest


SECRET_CASES = [
    ("github-token", "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB done"),
    ("github-token", "fine-grained github_pat_11ABCDEFG0_abcdefghijklmnopqrst"),
    ("aws-access-key", "creds AKIAIOSFODNN7EXAMPLE in env"),
    ("slack-token", "slack xoxb-" + "123456789012-abcdefghijklmnop here"),
    ("openai-key", "openai sk-proj-AbCdEf1234567890AbCdEf12 set"),
    ("jwt", "auth eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpM"),
    (
        "private-key-block",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
    ),
    ("url-credentials", "postgres://admin:s3cretpw@db.internal:5432/prod"),
    ("bearer-token", "header Authorization: Bearer abc123def456ghi789jkl012 sent"),
    ("env-assignment", "DATABASE_PASSWORD=hunter2hunter2 in .env"),
    ("env-assignment", 'export STRIPE_SECRET_KEY="whsec_abcdef123456"'),
]


@pytest.mark.parametrize(("detector", "text"), SECRET_CASES)
def test_secret_detectors(detector, text):
    redacted, counts = redact_text(text)
    assert counts.get(detector, 0) >= 1, f"{detector} did not fire on: {text!r}"
    assert f"[REDACTED:{detector}]" in redacted


def test_anthropic_key_not_double_matched_by_openai():
    redacted, counts = redact_text("key sk-ant-api03-AbCdEf123456789012345 x")
    assert counts.get("anthropic-key") == 1
    assert "openai-key" not in counts


def test_url_credentials_preserves_host():
    redacted, _ = redact_text("postgres://admin:s3cretpw@db.internal:5432/prod")
    assert "db.internal:5432/prod" in redacted
    assert "s3cretpw" not in redacted


def test_env_assignment_preserves_var_name():
    redacted, _ = redact_text("DATABASE_PASSWORD=hunter2hunter2")
    assert "DATABASE_PASSWORD=" in redacted
    assert "hunter2" not in redacted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_redaction.py -v`
Expected: the parametrized cases FAIL (detectors missing); Task 1 tests still PASS

- [ ] **Step 3: Implement the detector set**

Replace the `DETECTORS` tuple in `src/primer/common/redaction.py` with:

```python
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
)
```

Note the ordering: `private-key-block` before everything (multiline); `anthropic-key` before `openai-key` (both match `sk-`); `env-assignment` last with a `(?!\[REDACTED)` guard so it never re-wraps a value already replaced by a more specific detector, and a group-1 backreference so the variable *name* survives.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_redaction.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/primer/common/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): full secret detector set (vendor tokens, keys, jwt, env, urls)"
```

---

### Task 3: PII (email) detector and disabled-detectors support

**Files:**
- Modify: `src/primer/common/redaction.py`
- Modify: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_redaction.py
def test_email_detector():
    redacted, counts = redact_text("contact alice.smith+dev@example.co.uk for access")
    assert counts.get("email") == 1
    assert "alice.smith" not in redacted
    assert "[REDACTED:email]" in redacted


def test_disabled_detector_does_not_fire():
    text = "contact alice@example.com"
    redacted, counts = redact_text(text, disabled=frozenset({"email"}))
    assert redacted == text
    assert "email" not in counts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_redaction.py::test_email_detector -v`
Expected: FAIL (no email detector)

- [ ] **Step 3: Add the email detector**

Append to the `DETECTORS` tuple (after `env-assignment`):

```python
    Detector(
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
```

(The `disabled` parameter already exists from Task 1 — no engine change needed.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_redaction.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/primer/common/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): email PII detector with per-detector disable"
```

---

### Task 4: Idempotence property

**Files:**
- Modify: `tests/test_redaction.py`

- [ ] **Step 1: Write the idempotence test (expected to pass — this is a property lock-in)**

```python
# append to tests/test_redaction.py
ALL_CASE_TEXTS = [text for _, text in SECRET_CASES] + [
    "contact alice@example.com",
    "key sk-ant-api03-AbCdEf123456789012345",
    "mixed: ghp_abcdefghijklmnopqrstuvwxyz0123456789AB and PASSWORD=supersecret99 done",
]


@pytest.mark.parametrize("text", ALL_CASE_TEXTS)
def test_redaction_is_idempotent(text):
    once, _ = redact_text(text)
    twice, _ = redact_text(once)
    assert twice == once
```

- [ ] **Step 2: Run and fix any violations**

Run: `pytest tests/test_redaction.py -v`
Expected: ALL PASS. If an idempotence case fails, the offending detector is matching `[REDACTED:...]` tokens — add a `(?!\[REDACTED)` guard to that detector's pattern (as `bearer-token` and `env-assignment` already have) and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/test_redaction.py
git commit -m "test(redaction): lock in idempotence property across all detectors"
```

---

### Task 5: Settings and extra-pattern configuration

**Files:**
- Modify: `src/primer/common/config.py` (add after the facet extraction block, ~line 94)
- Modify: `src/primer/common/redaction.py`
- Modify: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_redaction.py
from primer.common.redaction import build_disabled_set, build_extra_detectors


def test_build_disabled_set_parses_csv():
    assert build_disabled_set("email, jwt") == frozenset({"email", "jwt"})
    assert build_disabled_set("") == frozenset()


def test_extra_detectors_from_json():
    extras = build_extra_detectors(
        '[{"name": "internal-id", "pattern": "EMP-[0-9]{6}"}]'
    )
    assert len(extras) == 1
    redacted, n = extras[0].apply("badge EMP-123456 issued")
    assert n == 1
    assert "[REDACTED:internal-id]" in redacted


def test_extra_detectors_invalid_json_returns_empty():
    assert build_extra_detectors("not json") == ()
    assert build_extra_detectors("") == ()


def test_redact_text_applies_extra_detectors():
    extras = build_extra_detectors('[{"name": "internal-id", "pattern": "EMP-[0-9]{6}"}]')
    redacted, counts = redact_text("badge EMP-123456", extra=extras)
    assert counts.get("internal-id") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_redaction.py::test_build_disabled_set_parses_csv -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement config helpers and the `extra` parameter**

Append to `src/primer/common/redaction.py`:

```python
import json
import logging

logger = logging.getLogger(__name__)


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
        return tuple(
            Detector(e["name"], re.compile(e["pattern"])) for e in entries
        )
    except (json.JSONDecodeError, KeyError, TypeError, re.error) as exc:
        logger.warning("Ignoring invalid PRIMER_REDACTION_EXTRA_PATTERNS: %s", exc)
        return ()
```

Then change `redact_text`'s signature and loop to accept extras:

```python
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
```

Move the `import json` / `import logging` lines to the top of the file with the other imports (ruff `I001` will flag them otherwise).

Add to `src/primer/common/config.py` after the facet-extraction settings block:

```python
    # Redaction (secret/PII scrubbing at capture and ingest)
    redaction_enabled: bool = True
    redaction_disabled_detectors: str = ""  # comma-separated detector names
    redaction_extra_patterns: str = ""  # JSON: [{"name": ..., "pattern": ...}]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_redaction.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/primer/common/redaction.py src/primer/common/config.py tests/test_redaction.py
git commit -m "feat(redaction): config-driven disable list and extra patterns"
```

---

### Task 6: Payload walker (`redact_ingest_dict`)

**Files:**
- Modify: `src/primer/common/redaction.py`
- Modify: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_redaction.py
from primer.common.redaction import redact_ingest_dict


def _payload_with_secrets() -> dict:
    return {
        "session_id": "sess-1",
        "api_key": "sk-ant-this-is-the-auth-key-not-content",
        "agent_type": "claude_code",
        "first_prompt": "set ANTHROPIC_API_KEY=sk-ant-api03-AbCdEf123456789012345",
        "summary": "Configured slack xoxb-" + "123456789012-abcdefghijklmnop webhook",
        "message_count": 2,
        "messages": [
            {
                "ordinal": 0,
                "role": "human",
                "content_text": "my token is ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
            },
            {
                "ordinal": 1,
                "role": "assistant",
                "content_text": "Done.",
                "tool_calls": [
                    {"name": "Bash", "input_preview": "export PASSWORD=hunter2hunter2"}
                ],
            },
            {
                "ordinal": 2,
                "role": "tool_result",
                "tool_results": [
                    {"name": "Bash", "output_preview": "postgres://admin:s3cret99@db/x"}
                ],
            },
        ],
        "commits": [
            {"sha": "abc123", "message": "fix: rotate AKIAIOSFODNN7EXAMPLE key"}
        ],
        "source_metadata": {"nested": {"note": "key sk-ant-api03-XyZ9876543210abcdef"}},
        "facets": {"goal_categories": ["uses sk-proj-AbCdEf1234567890AbCdEf12 key"]},
    }


def test_redact_ingest_dict_scrubs_all_text_fields():
    redacted, counts = redact_ingest_dict(_payload_with_secrets())
    assert "sk-ant-api03" not in str(redacted)
    assert "ghp_" not in str(redacted)
    assert "hunter2" not in str(redacted)
    assert "s3cret99" not in str(redacted)
    assert "AKIAIOSFODNN7EXAMPLE" not in str(redacted)
    assert "xoxb-" not in str(redacted)
    assert "sk-proj-" not in str(redacted)
    assert sum(counts.values()) >= 7


def test_redact_ingest_dict_never_touches_api_key_or_structure():
    payload = _payload_with_secrets()
    redacted, _ = redact_ingest_dict(payload)
    assert redacted["api_key"] == payload["api_key"]  # auth credential, not content
    assert redacted["session_id"] == "sess-1"
    assert redacted["message_count"] == 2
    assert redacted["messages"][0]["ordinal"] == 0
    assert redacted["commits"][0]["sha"] == "abc123"
    # input is not mutated
    assert "ghp_" in payload["messages"][0]["content_text"]


def test_redact_ingest_dict_handles_missing_fields():
    redacted, counts = redact_ingest_dict({"session_id": "s", "messages": None})
    assert redacted["session_id"] == "s"
    assert sum(counts.values()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_redaction.py::test_redact_ingest_dict_scrubs_all_text_fields -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement the walker**

Append to `src/primer/common/redaction.py`:

```python
import copy
from collections.abc import Iterable

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
        _redact_preview_items(
            message.get("tool_calls"), "input_preview", counts, disabled, extra
        )
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
```

Move `import copy` and the `collections.abc` import to the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_redaction.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/primer/common/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): whitelist payload walker for ingest payloads"
```

---

### Task 7: Hook wiring (client-side redaction before POST)

**Files:**
- Modify: `src/primer/hook/session_end.py`
- Modify: `tests/test_hook_session_end.py`

- [ ] **Step 1: Write the failing test**

Follow the existing mock pattern in `tests/test_hook_session_end.py` (see `test_main_prefers_device_token` for the template):

```python
# append to tests/test_hook_session_end.py
@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_redacts_payload_before_post(
    mock_get_extractor, mock_facets, mock_post, monkeypatch
):
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.setenv("PRIMER_DEVICE_TOKEN", "device-123")
    monkeypatch.delenv("PRIMER_REDACTION_ENABLED", raising=False)
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-redact", "transcript_path": "/t/x.jsonl"}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    meta = SessionMetadata(
        session_id="",
        first_prompt="my key is sk-ant-api03-AbCdEf123456789012345",
        messages=[
            {
                "ordinal": 0,
                "role": "human",
                "content_text": "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
            }
        ],
    )
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None
    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    sent = mock_post.call_args.kwargs["json"]
    assert "sk-ant-api03" not in sent["first_prompt"]
    assert "[REDACTED:anthropic-key]" in sent["first_prompt"]
    assert "ghp_" not in sent["messages"][0]["content_text"]


@patch("primer.hook.session_end.httpx.post")
@patch("primer.hook.session_end.load_facets")
@patch("primer.hook.session_end.get_extractor_for")
def test_main_redaction_can_be_disabled_by_env(
    mock_get_extractor, mock_facets, mock_post, monkeypatch
):
    monkeypatch.delenv("PRIMER_API_KEY", raising=False)
    monkeypatch.setenv("PRIMER_DEVICE_TOKEN", "device-123")
    monkeypatch.setenv("PRIMER_REDACTION_ENABLED", "false")
    monkeypatch.setattr(
        "sys.stdin",
        _make_stdin({"session_id": "sess-noredact", "transcript_path": "/t/x.jsonl"}),
    )
    monkeypatch.setattr("sys.argv", ["session_end"])

    meta = SessionMetadata(
        session_id="", first_prompt="key sk-ant-api03-AbCdEf123456789012345"
    )
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = meta
    mock_get_extractor.return_value = mock_extractor
    mock_facets.return_value = None
    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_post.return_value = mock_resp

    from primer.hook.session_end import main

    main()

    sent = mock_post.call_args.kwargs["json"]
    assert "sk-ant-api03" in sent["first_prompt"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hook_session_end.py::test_main_redacts_payload_before_post -v`
Expected: FAIL — `sk-ant-api03` still present in the posted payload

- [ ] **Step 3: Wire redaction into the hook**

In `src/primer/hook/session_end.py`, add to the imports:

```python
from primer.common.redaction import redact_ingest_dict
```

Then, immediately after `payload = meta.to_ingest_payload(api_key=api_key or None, facets=facets)` (line ~134), insert:

```python
    # Redact secrets/PII client-side before anything leaves this machine.
    # Controlled by PRIMER_REDACTION_ENABLED (default: on).
    if os.environ.get("PRIMER_REDACTION_ENABLED", "true").lower() not in ("0", "false", "no"):
        payload, redaction_counts = redact_ingest_dict(payload)
        if redaction_counts:
            logger.info(f"Redacted {sum(redaction_counts.values())} sensitive value(s)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hook_session_end.py -v`
Expected: ALL PASS (including the pre-existing tests — the redaction default must not break them)

- [ ] **Step 5: Commit**

```bash
git add src/primer/hook/session_end.py tests/test_hook_session_end.py
git commit -m "feat(hook): client-side redaction before session payload POST"
```

---

### Task 8: Server ingest chokepoint (single, bulk, async, sync)

**Files:**
- Modify: `src/primer/server/routers/ingest.py`
- Create: `tests/test_redaction_ingest.py`

- [ ] **Step 1: Write the failing integration tests**

```python
# tests/test_redaction_ingest.py
"""Integration tests: redaction at the server ingest chokepoint."""

import uuid

from primer.common.config import settings
from primer.common.models import BackgroundJob, SessionMessage
from primer.common.models import Session as SessionModel


def _secret_session_payload(api_key: str) -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "api_key": api_key,
        "agent_type": "claude_code",
        "first_prompt": "configure sk-ant-api03-AbCdEf123456789012345 now",
        "message_count": 1,
        "messages": [
            {
                "ordinal": 0,
                "role": "human",
                "content_text": "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
            }
        ],
    }


def test_sync_ingest_stores_redacted_messages(client, engineer_with_key, db_session):
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    session = (
        db_session.query(SessionModel)
        .filter(SessionModel.id == payload["session_id"])
        .one()
    )
    assert "sk-ant-api03" not in (session.first_prompt or "")
    assert "[REDACTED:anthropic-key]" in session.first_prompt

    msg = (
        db_session.query(SessionMessage)
        .filter(SessionMessage.session_id == payload["session_id"])
        .one()
    )
    assert "ghp_" not in (msg.content_text or "")


def test_async_ingest_job_payload_is_redacted(
    client, engineer_with_key, db_session, monkeypatch
):
    """The background_jobs table must never contain unredacted secrets."""
    monkeypatch.setattr(settings, "background_jobs_enabled", True)
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 202

    job = (
        db_session.query(BackgroundJob)
        .filter(BackgroundJob.job_type == "session_ingest")
        .order_by(BackgroundJob.created_at.desc())
        .first()
    )
    assert job is not None
    serialized = str(job.payload)
    assert "sk-ant-api03" not in serialized
    assert "ghp_" not in serialized


def test_bulk_ingest_stores_redacted_messages(client, engineer_with_key, db_session):
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/bulk", json={"sessions": [payload]})
    assert r.status_code == 200

    session = (
        db_session.query(SessionModel)
        .filter(SessionModel.id == payload["session_id"])
        .one()
    )
    assert "sk-ant-api03" not in (session.first_prompt or "")


def test_redaction_disabled_passes_through(client, engineer_with_key, db_session, monkeypatch):
    monkeypatch.setattr(settings, "redaction_enabled", False)
    _engineer, api_key = engineer_with_key
    payload = _secret_session_payload(api_key)

    r = client.post("/api/v1/ingest/session", json=payload)
    assert r.status_code == 200

    session = (
        db_session.query(SessionModel)
        .filter(SessionModel.id == payload["session_id"])
        .one()
    )
    assert "sk-ant-api03" in session.first_prompt
```

(Field name verified: `BulkIngestPayload.sessions` at `src/primer/common/schemas.py:483`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_redaction_ingest.py -v`
Expected: FAIL — secrets present in stored rows / job payloads

- [ ] **Step 3: Implement the chokepoint**

In `src/primer/server/routers/ingest.py`, add imports:

```python
from primer.common.redaction import (
    build_disabled_set,
    build_extra_detectors,
    redact_ingest_dict,
)
```

Add a module-level helper (near `_authenticate_ingest_engineer`):

```python
def _apply_redaction(payload: SessionIngestPayload) -> SessionIngestPayload:
    """Redact text-bearing fields before any persistence (incl. job queue)."""
    if not settings.redaction_enabled:
        return payload
    raw = payload.model_dump(mode="json")
    api_key = raw.pop("api_key", None)  # auth credential — exclude from the walk
    redacted, counts = redact_ingest_dict(
        raw,
        disabled=build_disabled_set(settings.redaction_disabled_detectors),
        extra=build_extra_detectors(settings.redaction_extra_patterns),
    )
    redacted["api_key"] = api_key
    if counts:
        logger.info(
            "Redacted %d sensitive value(s) in session %s",
            sum(counts.values()),
            payload.session_id,
        )
    return SessionIngestPayload(**redacted)
```

In `ingest_session`, immediately after the `engineer = _authenticate_ingest_engineer(...)` call and **before** the `if settings.background_jobs_enabled:` branch, insert:

```python
    payload = _apply_redaction(payload)
```

In `ingest_bulk`, apply the same line to each session payload at the top of the per-session loop:

```python
        session_payload = _apply_redaction(session_payload)
```

(Match the loop variable name used in the existing code at line ~145.)

(`logger` already exists in this module at `src/primer/server/routers/ingest.py:29` — no new import needed.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_redaction_ingest.py tests/test_ingest.py -v`
Expected: ALL PASS — including the pre-existing ingest suite (redaction must not alter clean payloads)

- [ ] **Step 5: Commit**

```bash
git add src/primer/server/routers/ingest.py tests/test_redaction_ingest.py
git commit -m "feat(ingest): server-side redaction chokepoint before any persistence"
```

---

### Task 9: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `pytest -q`
Expected: everything passes (baseline before this work: all green; nothing outside redaction/hook/ingest should change behavior)

- [ ] **Step 2: Lint and format**

Run: `ruff check . && ruff format --check .`
Expected: clean. Fix any `I001` import-order issues in `redaction.py` (the staged imports from Tasks 5–6 are the likely offenders).

- [ ] **Step 3: Security scan**

Run: `bandit -r src/ -c pyproject.toml`
Expected: clean (the regex literals are not flagged; if B105 fires on detector strings, add an inline `# noqa: S105` with a comment explaining these are *detector patterns*, not credentials)

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "chore(redaction): lint/format fixes" || echo "nothing to fix"
```

---

### Task 10: Documentation and roadmap

**Files:**
- Modify: `CLAUDE.md` (Key Paths backend table + Architecture Patterns)
- Modify: `ROADMAP.md` (mark the P0 item complete)

- [ ] **Step 1: Add the module to CLAUDE.md**

In the backend Key Paths table, add after the `pricing.py` row:

```markdown
| `src/primer/common/redaction.py` | Secret/PII redaction: named regex detectors + ingest-payload walker, applied in the hook (client-side) and ingest router (server-side) |
```

In Architecture Patterns, add:

```markdown
- **Redaction**: `src/primer/common/redaction.py` — whitelist walker over ingest payload text fields; runs client-side in the hook (`PRIMER_REDACTION_ENABLED`) and server-side in the ingest router before persistence (including the `background_jobs` table); configurable via `PRIMER_REDACTION_DISABLED_DETECTORS` / `PRIMER_REDACTION_EXTRA_PATTERNS`
```

- [ ] **Step 2: Update ROADMAP.md**

Locate the P0 line (currently `- \`P0\` Local secret, PII, and IP redaction pipeline at the capture layer before database insertion.` around line 69 and its checkbox twin around line 100) and mark the checkbox form `[x]`. Remove the bullet from Near-Term Priorities or annotate it as shipped, matching how previously completed items are handled in the file (see the `[x]` entries in the Measurement Integrity section for the convention).

- [ ] **Step 3: Final suite + commit**

```bash
pytest -q && ruff check .
git add CLAUDE.md ROADMAP.md
git commit -m "docs: redaction pipeline shipped — update CLAUDE.md and roadmap"
```

---

## Self-Review (completed)

- **Spec coverage:** §16 prerequisite #1 (redaction gates capture — both hook and server chokepoints covered, including the `background_jobs` persistence path the adversarial review flagged); §5 write-time safety (identity scrub for memory `body` text is **plan 2** scope — it operates on extracted memory cards, not raw payloads); §10 redaction gate (the `MEMORY_ENABLED` hard-fail check lands in plan 2 where that setting is introduced).
- **Placeholder scan:** no TBDs; every step has complete code; the one runtime-verification instruction (bulk payload field name) gives the exact grep command and adjustment rule.
- **Type consistency:** `redact_text(text, disabled, extra) -> tuple[str, dict[str, int]]`, `redact_ingest_dict(payload, disabled, extra) -> tuple[dict, dict[str, int]]`, `build_disabled_set(csv) -> frozenset[str]`, `build_extra_detectors(raw_json) -> tuple[Detector, ...]` — used consistently across Tasks 1–8.
