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
        (item.customization_type, item.state, item.identifier, item.provenance)
        for item in snapshots
    }
    assert ("command", "enabled", "ship", "repo_defined") in as_keys
    assert ("subagent", "enabled", "reviewer", "repo_defined") in as_keys
    assert ("template", "enabled", "bugfix", "repo_defined") in as_keys
    assert ("command", "enabled", "review-pr", "user_local") in as_keys
    assert ("skill", "enabled", "commit", "user_local") in as_keys
    assert ("mcp", "enabled", "github", "user_local") in as_keys
    assert ("mcp", "enabled", "linear", "repo_defined") in as_keys
    assert ("skill", "invoked", "commit", "user_local") in as_keys
    assert ("subagent", "invoked", "reviewer", "repo_defined") in as_keys
    assert ("mcp", "invoked", "github", "user_local") in as_keys

    invoked_github = next(
        item
        for item in snapshots
        if item.customization_type == "mcp"
        and item.state == "invoked"
        and item.identifier == "github"
    )
    assert invoked_github.invocation_count == 3


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

    roots = _candidate_project_roots(str(project))
    paths = [str(r) for r in roots]
    assert str(project) in paths
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
