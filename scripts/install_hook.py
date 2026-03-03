"""Install the Primer SessionEnd hook into an AI agent's settings.

Thin wrapper around primer.hook.installer — prefer `primer hook install`.
"""

import argparse

from primer.hook.installer import get_supported_agents, install


def install_hook() -> None:
    parser = argparse.ArgumentParser(description="Install the Primer SessionEnd hook")
    parser.add_argument(
        "--agent",
        default="claude",
        choices=get_supported_agents(),
        help="Agent to install the hook for (default: claude)",
    )
    args = parser.parse_args()
    _ok, msg = install(agent=args.agent)
    print(msg)


if __name__ == "__main__":
    install_hook()
