"""primer init — bootstrap ~/.primer/ with config and database."""

import secrets

import click


@click.command()
def init() -> None:
    """Initialize Primer: create config, run database migrations."""
    from primer.cli import console
    from primer.cli.config import DEFAULT_CONFIG, read_config, write_config
    from primer.cli.paths import CONFIG_FILE, DATABASE_FILE, ensure_dirs

    console.header("Initializing Primer")

    # 1. Create directories
    ensure_dirs()
    console.success("Created ~/.primer/")

    # 2. Generate config.toml (only if it doesn't exist)
    if CONFIG_FILE.exists():
        console.warn("Config file already exists, skipping generation.")
    else:
        admin_key = f"primer-admin-{secrets.token_hex(16)}"
        db_url = f"sqlite:///{DATABASE_FILE}"
        content = DEFAULT_CONFIG.replace(
            '# admin_api_key = "generated-on-init"',
            f'admin_api_key = "{admin_key}"',
        ).replace(
            '# url = "sqlite:///~/.primer/primer.db"',
            f'url = "{db_url}"',
        )
        write_config(content)
        console.success(f"Generated config at {CONFIG_FILE}")

    # 3. Load config into env before running migrations
    from primer.cli.config import load_config_into_env

    load_config_into_env()

    # 4. Run Alembic migrations programmatically
    cfg = read_config()
    db_url = cfg.get("database", {}).get("url", f"sqlite:///{DATABASE_FILE}")

    import os

    os.environ.setdefault("PRIMER_DATABASE_URL", db_url)

    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config()
        # Look for bundled alembic in package, fall back to project root
        import importlib.resources

        try:
            pkg_root = importlib.resources.files("primer")
            bundled_dir = pkg_root / "_alembic"
            bundled_ini = pkg_root / "_alembic.ini"
            if bundled_dir.is_dir():
                alembic_cfg.set_main_option("script_location", str(bundled_dir))
                if bundled_ini.is_file():
                    alembic_cfg.config_file_name = str(bundled_ini)
            else:
                raise FileNotFoundError
        except (FileNotFoundError, TypeError):
            # Development: use project-root alembic/
            from pathlib import Path

            project_root = Path(__file__).resolve().parents[4]
            alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
            ini_path = project_root / "alembic.ini"
            if ini_path.exists():
                alembic_cfg.config_file_name = str(ini_path)

        alembic_cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
        command.upgrade(alembic_cfg, "head")
        console.success("Database migrations applied.")
    except Exception as e:
        console.error(f"Migration failed: {e}")
        raise click.Abort from e

    console.header("Done! Next steps:")
    console.info("primer server start     — start the API server")
    console.info("primer setup            — register yourself as an engineer")
    console.info("primer hook install     — install the Claude Code hook")
