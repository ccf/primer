"""Install the Primer SessionEnd hook into Claude Code settings.

Thin wrapper around primer.hook.installer — prefer `primer hook install`.
"""

from primer.hook.installer import install


def install_hook() -> None:
    _ok, msg = install()
    print(msg)


if __name__ == "__main__":
    install_hook()
