from primer.server.services.change_shape_service import extract_change_shape


def test_extract_change_shape_from_mutating_tools_and_commits():
    messages = [
        {
            "ordinal": 0,
            "tool_calls": [
                {"name": "Write", "input_preview": '{"file_path":"src/auth.py"}'},
                {"name": "Edit", "input_preview": '{"path":"src/auth.py"}'},
                {"name": "Delete", "input_preview": '{"target_file":"tests/old_auth.py"}'},
                {"name": "Bash", "input_preview": '{"command":"git checkout -- src/auth.py"}'},
            ],
        }
    ]
    commits = [
        {
            "files_changed": 3,
            "lines_added": 40,
            "lines_deleted": 12,
            "message": "Update auth flow",
        }
    ]

    shape = extract_change_shape(messages, commits)

    assert shape is not None
    assert shape.files_touched_count == 3
    assert shape.named_touched_files == ["src/auth.py", "tests/old_auth.py"]
    assert shape.commit_files_changed == 3
    assert shape.lines_added == 40
    assert shape.lines_deleted == 12
    assert shape.diff_size == 52
    assert shape.edit_operations == 3
    assert shape.create_operations == 0
    assert shape.delete_operations == 1
    assert shape.rename_operations == 0
    assert shape.churn_files_count == 1
    assert shape.rewrite_indicator is True
    assert shape.revert_indicator is True


def test_extract_change_shape_falls_back_to_commit_stats_without_named_files():
    shape = extract_change_shape(
        messages=[],
        commits=[{"files_changed": 5, "lines_added": 20, "lines_deleted": 4}],
    )

    assert shape is not None
    assert shape.files_touched_count == 5
    assert shape.named_touched_files == []
    assert shape.commit_files_changed == 5
    assert shape.diff_size == 24
    assert shape.rewrite_indicator is False
    assert shape.revert_indicator is False


def test_extract_change_shape_returns_none_without_mutations():
    shape = extract_change_shape(
        messages=[
            {
                "ordinal": 0,
                "tool_calls": [{"name": "Read", "input_preview": '{"path":"src/auth.py"}'}],
            }
        ],
        commits=[],
    )

    assert shape is None
