"""Populate heartguard.users with load-testing accounts from users.csv."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "users.csv"


def read_credentials() -> Iterable[tuple[str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("users.csv is missing a header row")
        required = {"email", "password"}
        missing = required.difference(name.lower() for name in reader.fieldnames)
        if missing:
            raise ValueError(f"users.csv missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            email = (row.get("email") or "").strip().lower()
            password = (row.get("password") or "").strip()
            if not email or not password:
                continue
            yield email, password


def fetch_single_value(cur: psycopg.Cursor, sql: str, param: str) -> str:
    cur.execute(sql, (param,))
    result = cur.fetchone()
    if not result or not result[0]:
        raise LookupError(f"Value '{param}' not found for query: {sql}")
    return str(result[0])


def register_users(dsn: str) -> tuple[int, int]:
    credentials = list(read_credentials())
    if not credentials:
        return 0, 0

    with psycopg.connect(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET search_path TO heartguard, public")
            active_status_id = fetch_single_value(cur, "SELECT id FROM heartguard.user_statuses WHERE code = %s", "active")
            superadmin_role_id = fetch_single_value(cur, "SELECT id FROM heartguard.roles WHERE name = %s", "superadmin")

            inserted = 0
            updated = 0
            for index, (email, password) in enumerate(credentials, start=1):
                display_name = f"Load Tester {index:03d}"
                cur.execute(
                    """
                    INSERT INTO heartguard.users (
                        name,
                        email,
                        password_hash,
                        user_status_id,
                        two_factor_enabled,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        crypt(%s, gen_salt('bf', 10)),
                        %s,
                        FALSE,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (email) DO UPDATE
                    SET
                        password_hash = EXCLUDED.password_hash,
                        user_status_id = EXCLUDED.user_status_id,
                        updated_at = NOW()
                    RETURNING xmax = 0
                    """,
                    (
                        display_name,
                        email,
                        password,
                        active_status_id,
                    ),
                )
                was_insert = cur.fetchone()[0]
                if was_insert:
                    inserted += 1
                else:
                    updated += 1

                cur.execute(
                    """
                    INSERT INTO heartguard.user_role (user_id, role_id, assigned_at)
                    SELECT u.id, %s, NOW()
                    FROM heartguard.users AS u
                    WHERE u.email = %s
                    ON CONFLICT DO NOTHING
                    """,
                    (superadmin_role_id, email),
                )
        conn.commit()
    return inserted, updated


def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL environment variable is required")

    try:
        inserted, updated = register_users(dsn)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Failed to register users: {exc}") from exc

    print(f"Registered users -> inserted: {inserted}, updated: {updated}")


if __name__ == "__main__":
    main()
