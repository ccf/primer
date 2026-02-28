"""primer hook {install, uninstall, status} — manage the Claude Code hook."""

import click


@click.group()
def hook() -> None:
    """Manage the Claude Code SessionEnd hook."""


@hook.command()
def install() -> None:
    """Install the Primer SessionEnd hook."""
    from primer.cli import console
    from primer.hook.installer import install as do_install

    ok, msg = do_install()
    if ok:
        console.success(msg)
    else:
        console.error(msg)


@hook.command()
def uninstall() -> None:
    """Remove the Primer SessionEnd hook."""
    from primer.cli import console
    from primer.hook.installer import uninstall as do_uninstall

    ok, msg = do_uninstall()
    if ok:
        console.success(msg)
    else:
        console.error(msg)


@hook.command()
def status() -> None:
    """Check if the Primer hook is installed."""
    from primer.cli import console
    from primer.hook.installer import status as do_status

    installed, msg = do_status()
    if installed:
        console.success(msg)
    else:
        console.warn(msg)
