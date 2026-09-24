"""Copy the local SQLite scorecard into a configured Supabase PostgreSQL database."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
from urllib.parse import quote, urlsplit

from database import (
    DEFAULT_DATABASE_PATH,
    database_backend,
    database_info,
    initialize_database,
    load_assessments,
    load_setting,
    save_setting,
    upsert_assessments,
)


SETTING_KEYS = ("scorecard_configuration", "strategic_categories")
PASSWORD_PLACEHOLDER = "[YOUR-PASSWORD]"


def build_database_url(template: str, password: str) -> str:
    """Insert and URL-encode a password in an untouched Supabase URI template."""
    cleaned_template = template.strip()
    if PASSWORD_PLACEHOLDER not in cleaned_template:
        raise ValueError(
            f"Use the original Supabase URI containing {PASSWORD_PLACEHOLDER}."
        )
    if not password:
        raise ValueError("The database password cannot be empty.")
    database_url = cleaned_template.replace(
        PASSWORD_PLACEHOLDER,
        quote(password, safe=""),
        1,
    )
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("The Supabase URI must begin with postgresql://.")
    if not parsed.hostname or parsed.port != 5432 or parsed.path != "/postgres":
        raise ValueError("The URI must be the Supabase Session pooler URI on port 5432.")
    if not parsed.username or not parsed.username.startswith("postgres."):
        raise ValueError("The Session pooler username must begin with postgres.")
    return database_url


def migrate(source: Path) -> tuple[int, int]:
    if database_backend() != "PostgreSQL":
        raise RuntimeError("A PostgreSQL DATABASE_URL is required for the destination.")
    if not source.exists():
        raise FileNotFoundError(f"Local SQLite database not found: {source}")

    initialize_database()
    records = load_assessments(path=source)
    migrated_records = upsert_assessments(records)

    migrated_settings = 0
    missing = object()
    for key in SETTING_KEYS:
        value = load_setting(key, missing, path=source)
        if value is missing:
            continue
        save_setting(key, value)
        migrated_settings += 1
    return migrated_records, migrated_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy local Brand Scorecard data and settings to Supabase PostgreSQL."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help=f"SQLite source file (default: {DEFAULT_DATABASE_PATH})",
    )
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL", "").strip():
        template = input(
            "Paste the original Session pooler URI containing [YOUR-PASSWORD]: "
        ).strip()
        password = getpass.getpass("Paste the database password (input is hidden): ")
        try:
            os.environ["DATABASE_URL"] = build_database_url(template, password)
        except ValueError as exc:
            raise SystemExit(f"Migration cancelled: {exc}") from exc

    migrated_records, migrated_settings = migrate(args.source.expanduser().resolve())
    destination = database_info()
    print(
        f"Migration complete: {migrated_records} brand(s), "
        f"{migrated_settings} setting group(s), "
        f"{destination['records']} brand(s) now in Supabase."
    )


if __name__ == "__main__":
    main()
