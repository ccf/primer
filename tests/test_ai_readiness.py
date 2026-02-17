from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from primer.server.services.github_service import check_ai_readiness, sync_repository


def test_readiness_all_files():
    with patch("primer.server.services.github_service.check_file_exists", return_value=True):
        result = check_ai_readiness("org/repo", "main")
    assert result["has_claude_md"] is True
    assert result["has_agents_md"] is True
    assert result["has_claude_dir"] is True
    assert result["ai_readiness_score"] == 100.0


def test_readiness_claude_md_only():
    def fake_check(full_name, path, ref=None):
        return path == "CLAUDE.md"

    with patch("primer.server.services.github_service.check_file_exists", side_effect=fake_check):
        result = check_ai_readiness("org/repo")
    assert result["has_claude_md"] is True
    assert result["has_agents_md"] is False
    assert result["has_claude_dir"] is False
    assert result["ai_readiness_score"] == 50.0


def test_readiness_none():
    with patch("primer.server.services.github_service.check_file_exists", return_value=False):
        result = check_ai_readiness("org/repo")
    assert result["ai_readiness_score"] == 0.0


def test_readiness_cooldown(db_session):
    """Verify sync_repository skips readiness check if checked within 24h."""
    from primer.common.models import GitRepository

    repo = GitRepository(
        full_name="org/cooldown-test",
        has_claude_md=True,
        has_agents_md=False,
        has_claude_dir=False,
        ai_readiness_score=50.0,
        ai_readiness_checked_at=datetime.now(tz=UTC) - timedelta(hours=1),
    )
    db_session.add(repo)
    db_session.flush()

    with (
        patch("primer.server.services.github_service.is_configured", return_value=True),
        patch("primer.server.services.github_service.get_repository", return_value=None),
        patch("primer.server.services.github_service.list_pull_requests", return_value=[]),
        patch("primer.server.services.github_service.check_ai_readiness") as mock_readiness,
        patch(
            "primer.server.services.github_service.find_or_create_repository",
            return_value=repo,
        ),
    ):
        sync_repository(db_session, "org/cooldown-test")
        mock_readiness.assert_not_called()
