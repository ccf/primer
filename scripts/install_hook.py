"""Install the Primer SessionEnd hook into Claude Code settings.

Adds the hook to ~/.claude/settings.json so that every session end
triggers data upload to the Primer server.
"""

import json
from pathlib import Path


def install_hook() -> None:
    settings_path = Path.home() / ".claude" / "settings.json"

    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    hooks = settings.setdefault("hooks", {})
    session_end_hooks = hooks.setdefault("SessionEnd", [])

    hook_command = "python -m primer.hook.session_end"

    # Check if already installed
    for hook in session_end_hooks:
        if isinstance(hook, dict) and hook.get("command") == hook_command:
            print("Primer hook already installed.")
            return
        if isinstance(hook, str) and hook == hook_command:
            print("Primer hook already installed.")
            return

    session_end_hooks.append(
        {
            "command": hook_command,
            "timeout": 10000,
        }
    )

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"Primer SessionEnd hook installed in {settings_path}")
    print("Make sure PRIMER_API_KEY and PRIMER_SERVER_URL are set in your environment.")


if __name__ == "__main__":
    install_hook()
