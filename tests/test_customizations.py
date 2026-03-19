import json
from pathlib import Path

from primer.common.customizations import (
    _candidate_project_roots,
    _redact_mcp_config,
    build_session_customizations,
    is_explicit_customization_provenance,
)


def test_build_session_customizations_collects_enabled_and_invoked_items(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    claude_home = home_dir / ".claude"
    (claude_home / "commands").mkdir(parents=True)
    (claude_home / "skills").mkdir(parents=True)
    (claude_home / "commands" / "review-pr.md").write_text("# review-pr")
    (claude_home / "skills" / "commit.md").write_text("# commit")
    (claude_home / "settings.json").write_text(
        '{"mcpServers": {"github": {"command": "npx", "args": ['
        '"@modelcontextprotocol/server-github"]}}}'
    )

    project_dir = tmp_path / "repo"
    repo_claude = project_dir / ".claude"
    (repo_claude / "commands").mkdir(parents=True)
    (repo_claude / "agents").mkdir(parents=True)
    (repo_claude / "templates").mkdir(parents=True)
    (repo_claude / "commands" / "ship.md").write_text("# ship")
    (repo_claude / "agents" / "reviewer.md").write_text("# reviewer")
    (repo_claude / "templates" / "bugfix.md").write_text("# bugfix")
    (repo_claude / "settings.json").write_text(
        '{"mcpServers": {"linear": {"command": "npx", "args": ["linear-mcp"]}}}'
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    snapshots = build_session_customizations(
        "claude_code",
        str(project_dir),
        {
            "Skill:commit": 2,
            "Task:reviewer": 1,
            "mcp__github__fetch_pr_comments": 3,
            "Read": 5,
        },
    )

    as_keys = {
        (
            item.customization_type,
            item.state,
            item.identifier,
            item.provenance,
            item.source_classification,
        )
        for item in snapshots
    }
    assert ("command", "enabled", "ship", "repo_defined", "custom") in as_keys
    assert ("subagent", "enabled", "reviewer", "repo_defined", "custom") in as_keys
    assert ("template", "enabled", "bugfix", "repo_defined", "custom") in as_keys
    assert ("command", "enabled", "review-pr", "user_local", "custom") in as_keys
    assert ("skill", "enabled", "commit", "user_local", "custom") in as_keys
    assert ("mcp", "enabled", "github", "user_local", "marketplace") in as_keys
    assert ("mcp", "enabled", "linear", "repo_defined", "marketplace") in as_keys
    assert ("skill", "invoked", "commit", "user_local", "custom") in as_keys
    assert ("subagent", "invoked", "reviewer", "repo_defined", "custom") in as_keys
    assert ("mcp", "invoked", "github", "user_local", "marketplace") in as_keys

    invoked_github = next(
        item
        for item in snapshots
        if item.customization_type == "mcp"
        and item.state == "invoked"
        and item.identifier == "github"
    )
    assert invoked_github.invocation_count == 3
    assert invoked_github.source_classification == "marketplace"


def test_explicit_customization_provenance_filters_unknown_and_builtin():
    assert is_explicit_customization_provenance("repo_defined") is True
    assert is_explicit_customization_provenance("user_local") is True
    assert is_explicit_customization_provenance("unknown") is False
    assert is_explicit_customization_provenance("built_in") is False


def test_candidate_project_roots_traverses_nested_dirs(tmp_path, monkeypatch):
    """Projects nested inside $HOME should traverse intermediate directories."""
    home_dir = tmp_path / "home" / "user"
    home_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    monorepo = home_dir / "code" / "monorepo"
    project = monorepo / "packages" / "app"
    project.mkdir(parents=True)
    (monorepo / ".git").mkdir()
    (monorepo / ".claude").mkdir()
    (project / ".claude").mkdir()
    (project / "nested" / ".cursor").mkdir(parents=True)

    roots = _candidate_project_roots(str(project / "nested"), agent_type="cursor")
    paths = [str(r) for r in roots]
    assert str(project / "nested") in paths
    assert str(project) not in paths
    assert str(monorepo) in paths


def test_mcp_config_redacts_env_and_headers():
    config = {
        "command": "npx",
        "args": ["@server/github"],
        "env": {"GITHUB_TOKEN": "secret-token-123"},
        "headers": {"Authorization": "Bearer secret"},
    }
    redacted = _redact_mcp_config(config)
    assert "env" not in redacted
    assert "headers" not in redacted
    assert redacted["command"] == "npx"
    assert redacted["args"] == ["@server/github"]


def test_mcp_secrets_not_stored_in_details(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    project_dir = tmp_path / "repo"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "github": {
                        "command": "npx",
                        "args": ["@server/github"],
                        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_secret123"},
                    }
                }
            }
        )
    )

    snapshots = build_session_customizations("claude_code", str(project_dir), {})
    mcp_snap = next(s for s in snapshots if s.customization_type == "mcp" and s.state == "enabled")
    assert "env" not in mcp_snap.details
    assert mcp_snap.details["command"] == "npx"
    assert mcp_snap.source_classification == "marketplace"


def test_mcp_agent_family_cannot_be_overridden_by_user_config(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    project_dir = tmp_path / "repo"
    cursor_dir = project_dir / ".cursor"
    cursor_dir.mkdir(parents=True)
    (cursor_dir / "settings.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "linear": {
                        "command": "npx",
                        "agent_family": "spoofed-family",
                    }
                }
            }
        )
    )

    snapshots = build_session_customizations("cursor", str(project_dir), {})
    mcp_snap = next(s for s in snapshots if s.customization_type == "mcp" and s.state == "enabled")
    assert mcp_snap.details["agent_family"] == "cursor"


def test_build_session_customizations_scans_cursor_roots_and_prefers_cursor_provenance(
    tmp_path, monkeypatch
):
    home_dir = tmp_path / "home"
    cursor_home = home_dir / ".cursor"
    claude_home = home_dir / ".claude"
    (cursor_home / "skills").mkdir(parents=True)
    (claude_home / "skills").mkdir(parents=True)
    (cursor_home / "skills" / "review.md").write_text("# cursor review")
    (claude_home / "skills" / "review.md").write_text("# claude review")
    (cursor_home / "settings.json").write_text(
        '{"mcpServers": {"linear": {"command": "npx", "args": ["linear-mcp"]}}}'
    )

    project_dir = tmp_path / "repo"
    repo_cursor = project_dir / ".cursor"
    (repo_cursor / "agents").mkdir(parents=True)
    (repo_cursor / "agents" / "reviewer.md").write_text("# reviewer")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    snapshots = build_session_customizations(
        "cursor",
        str(project_dir),
        {
            "Skill:review": 2,
            "Task:reviewer": 1,
            "mcp__linear__query": 4,
        },
    )

    as_keys = {
        (
            item.customization_type,
            item.state,
            item.identifier,
            item.provenance,
            item.source_classification,
        )
        for item in snapshots
    }
    assert ("skill", "enabled", "review", "user_local", "custom") in as_keys
    assert ("subagent", "enabled", "reviewer", "repo_defined", "custom") in as_keys
    assert ("mcp", "enabled", "linear", "user_local", "marketplace") in as_keys
    assert ("skill", "invoked", "review", "user_local", "custom") in as_keys
    assert ("subagent", "invoked", "reviewer", "repo_defined", "custom") in as_keys
    assert ("mcp", "invoked", "linear", "user_local", "marketplace") in as_keys

    invoked_review = next(
        item
        for item in snapshots
        if item.customization_type == "skill"
        and item.state == "invoked"
        and item.identifier == "review"
    )
    assert invoked_review.source_path == str(cursor_home / "skills" / "review.md")
    assert invoked_review.details["raw_tool_name"] == "Skill:review"


def test_derive_invoked_customizations_classifies_builtin_skill_and_subagent():
    snapshots = build_session_customizations(
        "claude_code",
        None,
        {
            "Skill:explore": 1,
            "Task:plan": 2,
        },
    )

    as_keys = {
        (
            item.customization_type,
            item.state,
            item.identifier,
            item.provenance,
            item.source_classification,
        )
        for item in snapshots
    }

    assert ("skill", "invoked", "explore", "unknown", "built_in") in as_keys
    assert ("subagent", "invoked", "plan", "unknown", "built_in") in as_keys


def test_mcp_source_classification_marks_local_commands_as_custom(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    project_dir = tmp_path / "repo"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "local-tool": {
                        "command": "./scripts/local-mcp.py",
                    }
                }
            }
        )
    )

    snapshots = build_session_customizations("claude_code", str(project_dir), {})
    local_snap = next(
        s
        for s in snapshots
        if s.customization_type == "mcp" and s.state == "enabled" and s.identifier == "local-tool"
    )

    assert local_snap.source_classification == "custom"


def test_mcp_source_classification_marks_local_script_args_as_custom(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    project_dir = tmp_path / "repo"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "local-node-tool": {
                        "command": "node",
                        "args": ["src/mcp/main.js"],
                    }
                }
            }
        )
    )

    snapshots = build_session_customizations("claude_code", str(project_dir), {})
    local_snap = next(
        s
        for s in snapshots
        if s.customization_type == "mcp"
        and s.state == "enabled"
        and s.identifier == "local-node-tool"
    )

    assert local_snap.source_classification == "custom"


def test_unknown_agent_type_does_not_scan_other_agent_roots(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    claude_home = home_dir / ".claude"
    claude_home.mkdir(parents=True)
    (claude_home / "skills").mkdir(parents=True)
    (claude_home / "skills" / "review.md").write_text("# review")

    project_dir = tmp_path / "repo"
    repo_claude = project_dir / ".claude"
    repo_claude.mkdir(parents=True)
    (repo_claude / "commands").mkdir(parents=True)
    (repo_claude / "commands" / "ship.md").write_text("# ship")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    snapshots = build_session_customizations("unknown_agent", str(project_dir), {})
    assert snapshots == []


def test_candidate_project_roots_ignores_other_agent_markers_when_agent_known(
    tmp_path, monkeypatch
):
    home_dir = tmp_path / "home" / "user"
    home_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))

    root = home_dir / "repo"
    level_one = root / "apps"
    level_two = level_one / "web"
    level_three = level_two / "nested"
    level_three.mkdir(parents=True)

    (root / ".claude").mkdir()
    (level_one / ".cursor").mkdir()
    (level_two / ".gemini").mkdir()
    (level_three / ".codex").mkdir()

    roots = _candidate_project_roots(str(level_three), agent_type="claude_code")
    paths = [str(path) for path in roots]
    assert str(root) in paths
    assert str(level_one) not in paths
    assert str(level_two) not in paths
