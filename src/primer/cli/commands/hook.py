"""primer hook {install, uninstall, status, list} — manage AI agent hooks."""

import click


@click.group()
def hook() -> None:
    """Manage Primer SessionEnd hooks for AI coding agents."""


@hook.command()
@click.option(
    "--agent",
    type=click.Choice(["claude", "gemini"]),
    default="claude",
    help="Agent to install the hook for (default: claude).",
)
def install(agent: str) -> None:
    """Install the Primer SessionEnd hook."""
    from primer.cli import console
    from primer.hook.installer import install as do_install

    ok, msg = do_install(agent=agent)
    if ok:
        console.success(msg)
    else:
        console.error(msg)


@hook.command()
@click.option(
    "--agent",
    type=click.Choice(["claude", "gemini"]),
    default="claude",
    help="Agent to uninstall the hook for (default: claude).",
)
def uninstall(agent: str) -> None:
    """Remove the Primer SessionEnd hook."""
    from primer.cli import console
    from primer.hook.installer import uninstall as do_uninstall

    ok, msg = do_uninstall(agent=agent)
    if ok:
        console.success(msg)
    else:
        console.error(msg)


@hook.command()
@click.option(
    "--agent",
    type=click.Choice(["claude", "gemini"]),
    default="claude",
    help="Agent to check the hook for (default: claude).",
)
def status(agent: str) -> None:
    """Check if the Primer hook is installed."""
    from primer.cli import console
    from primer.hook.installer import status as do_status

    installed, msg = do_status(agent=agent)
    if installed:
        console.success(msg)
    else:
        console.warn(msg)


@hook.command("list")
def list_hooks() -> None:
    """Show hook status for all supported agents."""
    from primer.cli import console
    from primer.hook.installer import get_supported_agents
    from primer.hook.installer import status as do_status

    for agent in get_supported_agents():
        installed, msg = do_status(agent=agent)
        if installed:
            console.success(msg)
        else:
            console.warn(msg)
