from primer.server.services.workflow_profile_service import extract_session_workflow_profile


def test_extract_session_workflow_profile_maps_session_type_to_archetype():
    record = extract_session_workflow_profile(
        {"first_prompt": "Implement the billing export flow"},
        [
            {"tool_name": "Read", "call_count": 2},
            {"tool_name": "Edit", "call_count": 3},
            {"tool_name": "Bash", "call_count": 2},
        ],
        [
            {"evidence_type": "test"},
            {"evidence_type": "build"},
        ],
        change_shape={
            "files_touched_count": 3,
            "diff_size": 42,
            "edit_operations": 2,
        },
        facets={"session_type": "implementation"},
        has_commit=True,
    )

    assert record is not None
    assert record.archetype == "feature_delivery"
    assert record.archetype_source == "session_type"
    assert record.steps == ["read", "edit", "execute", "test", "ship"]
    assert record.label == "implementation: read -> edit -> execute -> test -> ship"


def test_extract_session_workflow_profile_detects_docs_work():
    record = extract_session_workflow_profile(
        {"first_prompt": "Update the README and onboarding docs"},
        [
            {"tool_name": "Read", "call_count": 1},
            {"tool_name": "Edit", "call_count": 2},
        ],
        [],
        change_shape={
            "files_touched_count": 2,
            "diff_size": 16,
            "edit_operations": 2,
            "named_touched_files": ["README.md", "docs/setup.md"],
        },
        has_commit=False,
    )

    assert record is not None
    assert record.archetype == "docs"
    assert record.archetype_source == "heuristic"
    assert "docs work" in (record.archetype_reason or "")


def test_extract_session_workflow_profile_detects_debugging_fix_loop():
    record = extract_session_workflow_profile(
        {"first_prompt": "Figure out why auth tests are failing"},
        [
            {"tool_name": "Edit", "call_count": 1},
            {"tool_name": "Bash", "call_count": 2},
        ],
        [{"evidence_type": "test"}],
        change_shape={
            "files_touched_count": 1,
            "diff_size": 12,
            "edit_operations": 1,
        },
        recovery_path={
            "recovery_step_count": 2,
            "recovery_result": "recovered",
            "recovery_strategies": ["edit_fix", "rerun_verification"],
        },
    )

    assert record is not None
    assert record.archetype == "debugging"
    assert record.steps == ["edit", "execute", "test", "fix"]
    assert record.verification_run_count == 1
