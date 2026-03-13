from primer.server.services.recovery_path_service import extract_recovery_path


def test_extract_recovery_path_detects_successful_recovery_after_failed_test():
    messages = [
        {
            "ordinal": 1,
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "Bash",
                    "input_preview": '{"command":"pytest tests/test_auth.py"}',
                }
            ],
        },
        {
            "ordinal": 2,
            "role": "assistant",
            "tool_calls": [{"name": "Edit", "input_preview": '{"file_path":"src/auth.py"}'}],
        },
        {
            "ordinal": 3,
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "Bash",
                    "input_preview": '{"command":"pytest tests/test_auth.py"}',
                }
            ],
        },
    ]
    execution_evidence = [
        {"ordinal": 1, "status": "failed", "command": "pytest tests/test_auth.py"},
        {"ordinal": 3, "status": "passed", "command": "pytest tests/test_auth.py"},
    ]
    facets = {"friction_counts": {"compile_error": 1}, "outcome": "success"}

    record = extract_recovery_path(messages, execution_evidence, facets)

    assert record is not None
    assert record.first_friction_ordinal == 1
    assert record.recovery_result == "recovered"
    assert record.recovery_step_count == 2
    assert record.recovery_strategies == ["edit_fix", "rerun_verification"]
    assert record.last_verification_status == "passed"
    assert record.sample_recovery_commands == ["pytest tests/test_auth.py"]


def test_extract_recovery_path_marks_abandoned_inspection_only_sessions():
    messages = [
        {
            "ordinal": 2,
            "role": "assistant",
            "tool_calls": [{"name": "Read", "input_preview": '{"file_path":"src/main.py"}'}],
        },
        {
            "ordinal": 3,
            "role": "assistant",
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"git status"}'}],
        },
    ]
    execution_evidence = [{"ordinal": 1, "status": "failed", "command": "pytest -q"}]
    facets = {"friction_counts": {"permission_denied": 2}, "outcome": "abandoned"}

    record = extract_recovery_path(messages, execution_evidence, facets)

    assert record is not None
    assert record.recovery_result == "abandoned"
    assert record.recovery_step_count == 2
    assert record.recovery_strategies == ["inspect_context"]
    assert record.last_verification_status is None
    assert record.sample_recovery_commands == ["git status"]
