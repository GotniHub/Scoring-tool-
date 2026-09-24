"""Persistent storage for the Advent+ Africa Brand Scorecard.

PostgreSQL is selected automatically when ``DATABASE_URL`` is configured.
Without it, SQLite remains the zero-configuration local fallback.  Passing an
explicit ``path`` always selects SQLite, which keeps local migrations and tests
isolated from the shared cloud database.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "brand_scorecard.db"


def database_url() -> str:
    """Return the configured PostgreSQL URL without ever logging it."""
    return os.getenv("DATABASE_URL", "").strip()


def database_path() -> Path:
    configured = os.getenv("BRAND_SCORECARD_DB_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DATABASE_PATH


def _uses_postgres(path: Path | None = None) -> bool:
    return path is None and bool(database_url())


def database_backend(path: Path | None = None) -> str:
    return "PostgreSQL" if _uses_postgres(path) else "SQLite"


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


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy missing values and scalars into strict JSON values."""
    value_type = type(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if value_type.__module__.startswith("pandas.") and value_type.__name__ in {
        "NAType",
        "NaTType",
    }:
        return None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, Path)):
        return str(value)
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _json_payload(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        default=_json_default,
        allow_nan=False,
    )


def _record_from_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return json.loads(value)


def _is_unique_violation(exc: Exception) -> bool:
    return isinstance(exc, sqlite3.IntegrityError) or getattr(exc, "sqlstate", None) == "23505"


@contextmanager
def _connection(path: Path | None = None) -> Iterator[Any]:
    if _uses_postgres(path):
        url = database_url()
        if not url.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string.")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires psycopg. Install the project requirements first."
            ) from exc

        connection = psycopg.connect(
            url,
            row_factory=dict_row,
            connect_timeout=15,
            prepare_threshold=None,
            sslmode="require",
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return

    target = Path(path) if path is not None else database_path()
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
        if _uses_postgres(path):
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    id BIGSERIAL PRIMARY KEY,
                    brand_name TEXT NOT NULL,
                    commercial_owner TEXT,
                    record_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_assessments_brand_name_lower
                ON assessments (LOWER(brand_name))
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_assessments_owner
                ON assessments(commercial_owner)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_json JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute("ALTER TABLE assessments ENABLE ROW LEVEL SECURITY")
            connection.execute("ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY")
            return

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
        order_expression = "LOWER(brand_name)" if _uses_postgres(path) else "brand_name COLLATE NOCASE"
        rows = connection.execute(
            f"SELECT record_json FROM assessments ORDER BY {order_expression}"
        ).fetchall()
    return [_record_from_json(row["record_json"]) for row in rows]


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
    payload = _json_payload(normalized_record)
    now = _utc_now()

    try:
        with _connection(path) as connection:
            if _uses_postgres(path):
                if previous_name and previous_name.casefold() != brand_name.casefold():
                    cursor = connection.execute(
                        """
                        UPDATE assessments
                        SET brand_name = %s, commercial_owner = %s,
                            record_json = %s::jsonb, updated_at = %s
                        WHERE LOWER(brand_name) = LOWER(%s)
                        """,
                        (brand_name, owner, payload, now, previous_name),
                    )
                    if cursor.rowcount:
                        return
                cursor = connection.execute(
                    """
                    UPDATE assessments
                    SET brand_name = %s, commercial_owner = %s,
                        record_json = %s::jsonb, updated_at = %s
                    WHERE LOWER(brand_name) = LOWER(%s)
                    """,
                    (brand_name, owner, payload, now, brand_name),
                )
                if cursor.rowcount:
                    return
                connection.execute(
                    """
                    INSERT INTO assessments (
                        brand_name, commercial_owner, record_json, created_at, updated_at
                    ) VALUES (%s, %s, %s::jsonb, %s, %s)
                    """,
                    (brand_name, owner, payload, now, now),
                )
                return

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
    except Exception as exc:
        if _is_unique_violation(exc):
            raise ValueError(f"A database record already exists for '{brand_name}'.") from exc
        raise


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
            record = _record_from_json(row["record_json"])
            if _clean_text(record.get("Status")).casefold() != source.casefold():
                continue
            record["Status"] = target
            payload = _json_payload(record)
            if _uses_postgres(path):
                connection.execute(
                    "UPDATE assessments SET record_json = %s::jsonb WHERE id = %s",
                    (payload, row["id"]),
                )
            else:
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
        if _uses_postgres(path):
            cursor = connection.execute(
                "DELETE FROM assessments WHERE LOWER(brand_name) = LOWER(%s)",
                (cleaned_name,),
            )
        else:
            cursor = connection.execute(
                "DELETE FROM assessments WHERE brand_name = ? COLLATE NOCASE",
                (cleaned_name,),
            )
    return cursor.rowcount > 0


def save_setting(key: str, value: Any, path: Path | None = None) -> None:
    initialize_database(path)
    payload = _json_payload(value)
    now = _utc_now()
    with _connection(path) as connection:
        if _uses_postgres(path):
            connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_json, updated_at)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_json = excluded.setting_json,
                    updated_at = excluded.updated_at
                """,
                (key, payload, now),
            )
            return
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
        if _uses_postgres(path):
            row = connection.execute(
                "SELECT setting_json FROM app_settings WHERE setting_key = %s", (key,)
            ).fetchone()
            return row["setting_json"] if row else default
        row = connection.execute(
            "SELECT setting_json FROM app_settings WHERE setting_key = ?", (key,)
        ).fetchone()
    return json.loads(row["setting_json"]) if row else default


def database_info(path: Path | None = None) -> dict[str, Any]:
    initialize_database(path)
    with _connection(path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS records, MAX(updated_at) AS last_updated FROM assessments"
        ).fetchone()
    postgres = _uses_postgres(path)
    last_updated = row["last_updated"]
    if isinstance(last_updated, datetime):
        last_updated = last_updated.isoformat(timespec="seconds")
    return {
        "backend": "Supabase PostgreSQL" if postgres else "SQLite",
        "path": "Supabase PostgreSQL" if postgres else str(Path(path) if path else database_path()),
        "records": int(row["records"]),
        "last_updated": last_updated,
    }
