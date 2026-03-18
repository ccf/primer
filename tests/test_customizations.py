from pathlib import Path

from primer.common.customizations import build_session_customizations


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
    assert ("skill", "invoked", "commit", "unknown") in as_keys
    assert ("subagent", "invoked", "reviewer", "unknown") in as_keys
    assert ("mcp", "invoked", "github", "unknown") in as_keys

    invoked_github = next(
        item
        for item in snapshots
        if item.customization_type == "mcp"
        and item.state == "invoked"
        and item.identifier == "github"
    )
    assert invoked_github.invocation_count == 3
