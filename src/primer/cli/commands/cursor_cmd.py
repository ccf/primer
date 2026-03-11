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
    try:
        meta = extractor.extract(str(bundle_path))
        session_id = extractor.validate_session_id(meta.session_id)
    except Exception as exc:
        raise click.ClickException(f"Invalid Cursor bundle: {exc}") from exc

    if meta.message_count == 0:
        raise click.ClickException("Invalid Cursor bundle: file contains no messages")

    store_suffix = ".jsonl" if bundle_path.suffix.lower() == ".jsonl" else ".json"
    store_path = extractor.get_sessions_dir() / f"{session_id}{store_suffix}"
    existing_paths = (
        extractor.get_sessions_dir() / f"{session_id}.json",
        extractor.get_sessions_dir() / f"{session_id}.jsonl",
    )
    if any(path.exists() for path in existing_paths):
        console.warn(f"Cursor session already imported: {session_id}")
        return

    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(bundle_path.read_bytes())
    console.success(f"Imported Cursor session: {session_id}")
