from primer.server.services.execution_evidence_service import extract_execution_evidence


def test_extract_execution_evidence_treats_zero_failures_and_zero_errors_as_passed():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"eslint ."}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash", "output_preview": "0 errors, 0 warnings"}],
        },
        {
            "ordinal": 2,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
        },
        {
            "ordinal": 3,
            "tool_results": [{"name": "Bash", "output_preview": "10 passed, 0 failed"}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("lint", "passed", "eslint ."),
        ("test", "passed", "pytest -q"),
    ]


def test_extract_execution_evidence_ignores_git_checkout_commands():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"git checkout main"}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash", "output_preview": "Switched to branch 'main'"}],
        },
        {
            "ordinal": 2,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"cargo check"}'}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("verification", "unknown", "cargo check")
    ]


def test_extract_execution_evidence_ignores_json_without_command_fields():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [
                {
                    "name": "Bash",
                    "input_preview": '{"description":"running eslint before review"}',
                }
            ],
        }
    ]

    evidence = extract_execution_evidence(messages)

    assert evidence == []


def test_extract_execution_evidence_treats_exit_code_zero_as_passed():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"cargo check"}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash", "output_preview": "Finished with exit code 0"}],
        },
        {
            "ordinal": 2,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
        },
        {
            "ordinal": 3,
            "tool_results": [{"name": "Bash", "output_preview": "Finished with exit code 2"}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("verification", "passed", "cargo check"),
        ("test", "failed", "pytest -q"),
    ]


def test_extract_execution_evidence_does_not_treat_v20_failed_as_success():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash", "output_preview": "test_v20 failed to compile"}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("test", "failed", "pytest -q")
    ]


def test_extract_execution_evidence_consumes_pending_record_without_output():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"pytest -q"}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash"}],
        },
        {
            "ordinal": 2,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"ruff check ."}'}],
        },
        {
            "ordinal": 3,
            "tool_results": [{"name": "Bash", "output_preview": "Found 1 error"}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    observed = [
        (row.evidence_type, row.status, row.command, row.output_preview) for row in evidence
    ]

    assert observed == [
        ("test", "unknown", "pytest -q", None),
        ("lint", "failed", "ruff check .", "Found 1 error"),
    ]


def test_extract_execution_evidence_treats_zero_failures_as_passed():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [{"name": "Bash", "input_preview": '{"command":"rspec"}'}],
        },
        {
            "ordinal": 1,
            "tool_results": [{"name": "Bash", "output_preview": "5 examples, 0 failures"}],
        },
    ]

    evidence = extract_execution_evidence(messages)

    assert [(row.evidence_type, row.status, row.command) for row in evidence] == [
        ("test", "passed", "rspec")
    ]
