"""Shared utility functions."""

import re
from datetime import datetime


def parse_repo_full_name(url: str) -> str | None:
    """Extract owner/repo from a git remote URL.

    Supports SSH (git@github.com:owner/repo.git)
    and HTTPS (https://github.com/owner/repo.git) formats.
    """
    # SSH: git@github.com:owner/repo.git
    m = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    # HTTPS: https://github.com/owner/repo.git
    m = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    return None


def parse_github_datetime(val: str | None) -> datetime | None:
    """Parse an ISO datetime string from GitHub (handles trailing Z)."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
