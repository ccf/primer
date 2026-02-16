"""Shared utility functions."""

import re


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
