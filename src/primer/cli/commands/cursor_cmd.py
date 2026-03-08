"""primer cursor import — manage Primer-owned Cursor bundles."""

from pathlib import Path

import click

from primer.hook.cursor_extractor import CursorExtractor


@click.group("cursor")
def cursor() -> None:
    """Manage imported Cursor session bundles."""


@cursor.command("import")
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def import_bundle(bundle_path: Path) -> None:
    """Validate and import a Cursor bundle into Primer-managed local storage."""
    from primer.cli import console

    extractor = CursorExtractor()
    meta = extractor.extract(str(bundle_path))
    try:
        store_path = extractor.get_session_path(meta.session_id)
    except ValueError as exc:
        raise click.ClickException(f"Invalid Cursor bundle: {exc}") from exc

    if store_path.exists():
        console.warn(f"Cursor session already imported: {meta.session_id}")
        return

    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(bundle_path.read_bytes())
    console.success(f"Imported Cursor session: {meta.session_id}")
