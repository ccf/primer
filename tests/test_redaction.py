"""Tests for the secret/PII redaction pipeline."""

import pytest

from primer.common.redaction import (
    build_disabled_set,
    build_extra_detectors,
    redact_ingest_dict,
    redact_text,
)


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


# Assembled at runtime with `+` so the Slack-shaped literal never appears
# contiguously in source. GitHub push protection (and other secret scanners)
# match the assembled form; implicit adjacent-literal concatenation is NOT
# safe here because ruff-format rejoins adjacent literals into one.
FAKE_SLACK_TOKEN = "xoxb-" + "123456789012-abcdefghijklmnop"

SECRET_CASES = [
    ("github-token", "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB done"),
    ("github-token", "fine-grained github_pat_11ABCDEFG0_abcdefghijklmnopqrst"),
    ("aws-access-key", "creds AKIAIOSFODNN7EXAMPLE in env"),
    ("slack-token", f"slack {FAKE_SLACK_TOKEN} here"),
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
    _redacted, counts = redact_text("key sk-ant-api03-AbCdEf123456789012345 x")
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


def test_build_disabled_set_parses_csv():
    assert build_disabled_set("email, jwt") == frozenset({"email", "jwt"})
    assert build_disabled_set("") == frozenset()


def test_extra_detectors_from_json():
    extras = build_extra_detectors('[{"name": "internal-id", "pattern": "EMP-[0-9]{6}"}]')
    assert len(extras) == 1
    redacted, n = extras[0].apply("badge EMP-123456 issued")
    assert n == 1
    assert "[REDACTED:internal-id]" in redacted


def test_extra_detectors_invalid_json_returns_empty():
    assert build_extra_detectors("not json") == ()
    assert build_extra_detectors("") == ()


def test_redact_text_applies_extra_detectors():
    extras = build_extra_detectors('[{"name": "internal-id", "pattern": "EMP-[0-9]{6}"}]')
    _redacted, counts = redact_text("badge EMP-123456", extra=extras)
    assert counts.get("internal-id") == 1


def _payload_with_secrets() -> dict:
    return {
        "session_id": "sess-1",
        "api_key": "sk-ant-this-is-the-auth-key-not-content",
        "agent_type": "claude_code",
        "first_prompt": "set ANTHROPIC_API_KEY=sk-ant-api03-AbCdEf123456789012345",
        "summary": f"Configured slack {FAKE_SLACK_TOKEN} webhook",
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
                "tool_calls": [{"name": "Bash", "input_preview": "export PASSWORD=hunter2hunter2"}],
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
            {
                "sha": "abc123",
                "message": "fix: rotate AKIAIOSFODNN7EXAMPLE key",
                "author_email": "teammate@example.com",
            }
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
    assert "teammate@example.com" not in str(redacted)
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


def test_commit_author_email_respects_disabled_email_detector():
    payload = _payload_with_secrets()
    redacted, _ = redact_ingest_dict(payload, disabled=frozenset({"email"}))
    assert redacted["commits"][0]["author_email"] == "teammate@example.com"


def test_env_assignment_ignores_short_values():
    _, counts = redact_text("retry_token: abc12")
    assert "env-assignment" not in counts


def test_env_assignment_yaml_colon_fires_by_design():
    # Over-redaction is the safe failure mode: YAML transcripts carry real
    # secrets (docker-compose, k8s), so `key: value` syntax is in scope even
    # though it can mask innocent flag names.
    _, counts = redact_text("api_token: my-feature-flag-key-prod")
    assert counts.get("env-assignment") == 1


def test_short_sk_prefix_not_matched():
    text = "the sk-learn package and sk-proj-short ids"
    redacted, counts = redact_text(text)
    assert "openai-key" not in counts
    assert redacted == text


def test_unterminated_private_key_block_does_not_hang():
    text = "-----BEGIN RSA PRIVATE KEY-----\n" + ("x" * 100_000)
    _redacted, counts = redact_text(text)
    assert "private-key-block" not in counts
