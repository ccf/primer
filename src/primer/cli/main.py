"""Primer CLI — unified command-line interface.

Entry point: `primer` (registered via pyproject.toml [project.scripts]).
"""

import click

from primer.cli.commands.configure import configure
from primer.cli.commands.cursor_cmd import cursor
from primer.cli.commands.doctor import doctor
from primer.cli.commands.hook import hook
from primer.cli.commands.init import init
from primer.cli.commands.mcp_cmd import mcp
from primer.cli.commands.server import server
from primer.cli.commands.setup import setup
from primer.cli.commands.sync_cmd import sync


@click.group()
@click.version_option(package_name="primer")
def cli() -> None:
    """Primer — Claude Code usage insights for your team."""
    from primer.cli.config import load_config_into_env

    load_config_into_env()


cli.add_command(init)
cli.add_command(setup)
cli.add_command(server)
cli.add_command(hook)
cli.add_command(mcp)
cli.add_command(sync)
cli.add_command(doctor)
cli.add_command(configure)
cli.add_command(cursor)
