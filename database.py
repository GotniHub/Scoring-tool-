"""Persistent storage for the Advent+ Africa Brand Scorecard.

SQLite is the zero-configuration default.  The database path can be overridden
with BRAND_SCORECARD_DB_PATH, which also keeps tests and deployments isolated.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "brand_scorecard.db"


def database_path() -> Path:
    configured = os.getenv("BRAND_SCORECARD_DB_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DATABASE_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"<na>", "nan", "none", "nat"} else text


def _json_default(value: Any) -> Any:
    try:
        if bool(value != value):  # NaN and pandas NA-like scalar values
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (datetime, Path)):
        return str(value)
    return None


@contextmanager
def _connection(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: Path | None = None) -> None:
    with _connection(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                commercial_owner TEXT,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_assessments_owner
            ON assessments(commercial_owner);

            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def load_assessments(path: Path | None = None) -> list[dict[str, Any]]:
    initialize_database(path)
    with _connection(path) as connection:
        rows = connection.execute(
            "SELECT record_json FROM assessments ORDER BY brand_name COLLATE NOCASE"
        ).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def upsert_assessment(
    record: dict[str, Any],
    previous_name: str | None = None,
    path: Path | None = None,
) -> None:
    initialize_database(path)
    brand_name = _clean_text(record.get("Brand name"))
    if not brand_name:
        raise ValueError("Brand name is required before saving to the database.")
    owner = _clean_text(record.get("Commercial owner")) or None
    normalized_record = dict(record)
    normalized_record["Brand name"] = brand_name
    payload = json.dumps(normalized_record, ensure_ascii=False, default=_json_default)
    now = _utc_now()

    try:
        with _connection(path) as connection:
            if previous_name and previous_name.casefold() != brand_name.casefold():
                cursor = connection.execute(
                    """
                    UPDATE assessments
                    SET brand_name = ?, commercial_owner = ?, record_json = ?, updated_at = ?
                    WHERE brand_name = ? COLLATE NOCASE
                    """,
                    (brand_name, owner, payload, now, previous_name),
                )
                if cursor.rowcount:
                    return
            connection.execute(
                """
                INSERT INTO assessments (
                    brand_name, commercial_owner, record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(brand_name) DO UPDATE SET
                    commercial_owner = excluded.commercial_owner,
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (brand_name, owner, payload, now, now),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"A database record already exists for '{brand_name}'.") from exc


def upsert_assessments(records: Iterable[dict[str, Any]], path: Path | None = None) -> int:
    count = 0
    for record in records:
        brand_name = _clean_text(record.get("Brand name"))
        if not brand_name:
            continue
        upsert_assessment(record, path=path)
        count += 1
    return count


def rename_assessment_status(
    old_status: str,
    new_status: str,
    path: Path | None = None,
) -> int:
    """Rename a stored workflow status without changing business update dates."""
    initialize_database(path)
    source = _clean_text(old_status)
    target = _clean_text(new_status)
    if not source or not target:
        raise ValueError("Both the old and new status values are required.")
    migrated = 0
    with _connection(path) as connection:
        rows = connection.execute("SELECT id, record_json FROM assessments").fetchall()
        for row in rows:
            record = json.loads(row["record_json"])
            if _clean_text(record.get("Status")).casefold() != source.casefold():
                continue
            record["Status"] = target
            payload = json.dumps(record, ensure_ascii=False, default=_json_default)
            connection.execute(
                "UPDATE assessments SET record_json = ? WHERE id = ?",
                (payload, row["id"]),
            )
            migrated += 1
    return migrated


def delete_assessment(brand_name: str, path: Path | None = None) -> bool:
    """Delete one assessment by brand name and report whether it existed."""
    initialize_database(path)
    cleaned_name = _clean_text(brand_name)
    if not cleaned_name:
        raise ValueError("Brand name is required before deleting from the database.")
    with _connection(path) as connection:
        cursor = connection.execute(
            "DELETE FROM assessments WHERE brand_name = ? COLLATE NOCASE",
            (cleaned_name,),
        )
    return cursor.rowcount > 0


def save_setting(key: str, value: Any, path: Path | None = None) -> None:
    initialize_database(path)
    payload = json.dumps(value, ensure_ascii=False, default=_json_default)
    now = _utc_now()
    with _connection(path) as connection:
        connection.execute(
            """
            INSERT INTO app_settings (setting_key, setting_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_json = excluded.setting_json,
                updated_at = excluded.updated_at
            """,
            (key, payload, now),
        )


def load_setting(key: str, default: Any = None, path: Path | None = None) -> Any:
    initialize_database(path)
    with _connection(path) as connection:
        row = connection.execute(
            "SELECT setting_json FROM app_settings WHERE setting_key = ?", (key,)
        ).fetchone()
    return json.loads(row["setting_json"]) if row else default


def database_info(path: Path | None = None) -> dict[str, Any]:
    target = path or database_path()
    initialize_database(target)
    with _connection(target) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS records, MAX(updated_at) AS last_updated FROM assessments"
        ).fetchone()
    return {
        "path": str(target),
        "records": int(row["records"]),
        "last_updated": row["last_updated"],
    }
