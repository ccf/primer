"""Colored output helpers for CLI commands."""

import click


def success(msg: str) -> None:
    click.secho(f"  ✓ {msg}", fg="green")


def error(msg: str) -> None:
    click.secho(f"  ✗ {msg}", fg="red")


def warn(msg: str) -> None:
    click.secho(f"  ! {msg}", fg="yellow")


def info(msg: str) -> None:
    click.secho(f"  → {msg}", fg="cyan")


def header(msg: str) -> None:
    click.secho(f"\n{msg}", fg="white", bold=True)


def kvp(key: str, value: str) -> None:
    click.echo(f"  {click.style(key + ':', fg='white', bold=True)} {value}")
