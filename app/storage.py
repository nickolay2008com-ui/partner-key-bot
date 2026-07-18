from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class SavedReport:
    id: int
    user_id: int
    partner_name: str
    birth_date: str
    emotional_language_title: str
    created_at: str


DEFAULT_PROFILE: dict[str, str] = {
    "self_name": "",
    "self_birth_date": "",
    "partner_name": "",
    "partner_birth_date": "",
}


class ReportsStore:
    def __init__(self, db_path: Path, database_url: str | None = None) -> None:
        self.db_path = db_path
        self.database_url = database_url.strip() if database_url else None
        if self.database_url:
            self._init_postgres_db()
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite_db()

    def _connect_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_postgres(self) -> psycopg.Connection[dict[str, Any]]:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_sqlite_db(self) -> None:
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS partner_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    partner_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    emotional_language TEXT NOT NULL,
                    emotional_language_title TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_partner_reports_user_id ON partner_reports(user_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS report_generation_requests (
                    user_id INTEGER NOT NULL,
                    launch_token TEXT NOT NULL,
                    report_id INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, launch_token)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id INTEGER PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS broadcast_log (
                    broadcast_key TEXT PRIMARY KEY,
                    sent_at TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    success INTEGER NOT NULL,
                    failed INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    self_name TEXT NOT NULL DEFAULT '',
                    self_birth_date TEXT NOT NULL DEFAULT '',
                    partner_name TEXT NOT NULL DEFAULT '',
                    partner_birth_date TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_name TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_name ON analytics_events(event_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS premium_entitlements (
                    user_id INTEGER NOT NULL,
                    product_key TEXT NOT NULL,
                    report_id INTEGER NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    payment_payload TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, product_key, report_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_premium_entitlements_user_id ON premium_entitlements(user_id)")

    def _init_postgres_db(self) -> None:
        with self._connect_postgres() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS partner_reports (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    partner_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    emotional_language TEXT NOT NULL,
                    emotional_language_title TEXT NOT NULL,
                    report_json JSONB NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_partner_reports_user_id ON partner_reports(user_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS report_generation_requests (
                    user_id BIGINT NOT NULL,
                    launch_token TEXT NOT NULL,
                    report_id BIGINT NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, launch_token)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id BIGINT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS broadcast_log (
                    broadcast_key TEXT PRIMARY KEY,
                    sent_at TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    success INTEGER NOT NULL,
                    failed INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id BIGINT PRIMARY KEY,
                    self_name TEXT NOT NULL DEFAULT '',
                    self_birth_date TEXT NOT NULL DEFAULT '',
                    partner_name TEXT NOT NULL DEFAULT '',
                    partner_birth_date TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    user_id BIGINT,
                    event_name TEXT NOT NULL,
                    event_json JSONB NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_name ON analytics_events(event_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS premium_entitlements (
                    user_id BIGINT NOT NULL,
                    product_key TEXT NOT NULL,
                    report_id BIGINT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    payment_payload TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, product_key, report_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_premium_entitlements_user_id ON premium_entitlements(user_id)")

    def register_user(self, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    """
                    INSERT INTO bot_users (user_id, first_seen_at, last_seen_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(user_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                    """,
                    (user_id, now, now),
                )
            return
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                INSERT INTO bot_users (user_id, first_seen_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (user_id, now, now),
            )

    def add(self, user_id: int, report: object) -> int:
        self.register_user(user_id)
        payload = report.to_dict()  # PartnerReport-like object. Keep storage decoupled.
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._connect_postgres() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO partner_reports (
                        user_id, partner_name, birth_date, emotional_language,
                        emotional_language_title, report_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        payload["partner_name"],
                        payload["birth_date"],
                        payload["emotional_language"],
                        payload["emotional_language_title"],
                        json.dumps(payload, ensure_ascii=False),
                        now,
                    ),
                )
                row = cursor.fetchone()
                return int(row["id"] if row else 0)
        with self._connect_sqlite() as conn:
            cursor = conn.execute(
                """
                INSERT INTO partner_reports (
                    user_id, partner_name, birth_date, emotional_language,
                    emotional_language_title, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    payload["partner_name"],
                    payload["birth_date"],
                    payload["emotional_language"],
                    payload["emotional_language_title"],
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def add_idempotent(self, user_id: int, report: object, launch_token: str) -> tuple[int, bool]:
        """Store one report for a concrete launch token.

        A repeated, intentional launch receives a new token and may create another
        report for the same date. Retries and concurrent handlers for one launch
        reuse the first stored report instead of duplicating it.
        """
        safe_token = str(launch_token or "").strip()[:80]
        if not safe_token:
            raise ValueError("launch_token is required")

        self.register_user(user_id)
        payload = report.to_dict()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if self.database_url:
            with self._connect_postgres() as conn:
                reservation = conn.execute(
                    """
                    INSERT INTO report_generation_requests (user_id, launch_token, report_id, created_at)
                    VALUES (%s, %s, 0, %s)
                    ON CONFLICT(user_id, launch_token) DO NOTHING
                    RETURNING launch_token
                    """,
                    (user_id, safe_token, now),
                ).fetchone()
                if reservation is None:
                    existing = conn.execute(
                        """
                        SELECT report_id
                        FROM report_generation_requests
                        WHERE user_id = %s AND launch_token = %s
                        """,
                        (user_id, safe_token),
                    ).fetchone()
                    report_id = int(existing["report_id"] if existing else 0)
                    if report_id <= 0:
                        raise RuntimeError("report generation reservation is incomplete")
                    return report_id, False

                cursor = conn.execute(
                    """
                    INSERT INTO partner_reports (
                        user_id, partner_name, birth_date, emotional_language,
                        emotional_language_title, report_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        payload["partner_name"],
                        payload["birth_date"],
                        payload["emotional_language"],
                        payload["emotional_language_title"],
                        json.dumps(payload, ensure_ascii=False),
                        now,
                    ),
                )
                row = cursor.fetchone()
                report_id = int(row["id"] if row else 0)
                if report_id <= 0:
                    raise RuntimeError("stored report did not return an id")
                conn.execute(
                    """
                    UPDATE report_generation_requests
                    SET report_id = %s
                    WHERE user_id = %s AND launch_token = %s
                    """,
                    (report_id, user_id, safe_token),
                )
                return report_id, True

        with self._connect_sqlite() as conn:
            reservation = conn.execute(
                """
                INSERT OR IGNORE INTO report_generation_requests (user_id, launch_token, report_id, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (user_id, safe_token, now),
            )
            if reservation.rowcount == 0:
                existing = conn.execute(
                    """
                    SELECT report_id
                    FROM report_generation_requests
                    WHERE user_id = ? AND launch_token = ?
                    """,
                    (user_id, safe_token),
                ).fetchone()
                report_id = int(existing["report_id"] if existing else 0)
                if report_id <= 0:
                    raise RuntimeError("report generation reservation is incomplete")
                return report_id, False

            cursor = conn.execute(
                """
                INSERT INTO partner_reports (
                    user_id, partner_name, birth_date, emotional_language,
                    emotional_language_title, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    payload["partner_name"],
                    payload["birth_date"],
                    payload["emotional_language"],
                    payload["emotional_language_title"],
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )
            report_id = int(cursor.lastrowid)
            conn.execute(
                """
                UPDATE report_generation_requests
                SET report_id = ?
                WHERE user_id = ? AND launch_token = ?
                """,
                (report_id, user_id, safe_token),
            )
            return report_id, True

    def replace_report(self, user_id: int, report_id: int, report: object) -> bool:
        """Replace one stored report after verifying ownership."""
        payload = report.to_dict()
        serialized = json.dumps(payload, ensure_ascii=False)
        values = (
            payload["partner_name"],
            payload["birth_date"],
            payload["emotional_language"],
            payload["emotional_language_title"],
            serialized,
            user_id,
            report_id,
        )
        if self.database_url:
            with self._connect_postgres() as conn:
                cursor = conn.execute(
                    """
                    UPDATE partner_reports
                    SET partner_name = %s,
                        birth_date = %s,
                        emotional_language = %s,
                        emotional_language_title = %s,
                        report_json = %s::jsonb
                    WHERE user_id = %s AND id = %s
                    """,
                    values,
                )
                return cursor.rowcount == 1
        with self._connect_sqlite() as conn:
            cursor = conn.execute(
                """
                UPDATE partner_reports
                SET partner_name = ?,
                    birth_date = ?,
                    emotional_language = ?,
                    emotional_language_title = ?,
                    report_json = ?
                WHERE user_id = ? AND id = ?
                """,
                values,
            )
            return cursor.rowcount == 1

    def latest_report_payload(self, user_id: int) -> dict[str, Any] | None:
        self.register_user(user_id)
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT id, report_json
                    FROM partner_reports
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT id, report_json
                    FROM partner_reports
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        if row is None:
            return None
        raw_payload = row["report_json"]
        payload = raw_payload if isinstance(raw_payload, dict) else json.loads(str(raw_payload))
        if not isinstance(payload, dict):
            return None
        payload["_storage_report_id"] = int(row["id"])
        return payload

    def report_payload(self, user_id: int, report_id: int) -> dict[str, Any] | None:
        """Return one report owned by the user, including its storage identifier."""
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT id, report_json
                    FROM partner_reports
                    WHERE user_id = %s AND id = %s
                    LIMIT 1
                    """,
                    (user_id, report_id),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT id, report_json
                    FROM partner_reports
                    WHERE user_id = ? AND id = ?
                    LIMIT 1
                    """,
                    (user_id, report_id),
                ).fetchone()
        if row is None:
            return None
        raw_payload = row["report_json"]
        payload = raw_payload if isinstance(raw_payload, dict) else json.loads(str(raw_payload))
        if not isinstance(payload, dict):
            return None
        payload["_storage_report_id"] = int(row["id"])
        return payload

    def has_any_entitlement(self, user_id: int, report_id: int) -> bool:
        """Return whether at least one paid product is attached to a report."""
        self.register_user(user_id)
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT 1 FROM premium_entitlements
                    WHERE user_id = %s AND report_id = %s
                    LIMIT 1
                    """,
                    (user_id, report_id),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT 1 FROM premium_entitlements
                    WHERE user_id = ? AND report_id = ?
                    LIMIT 1
                    """,
                    (user_id, report_id),
                ).fetchone()
        return row is not None

    def has_saved_reports(self, user_id: int) -> bool:
        """Return whether the user has at least one completed stored report."""
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM partner_reports
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM partner_reports
                    WHERE user_id = ?
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        return row is not None

    def is_latest_report(self, user_id: int, report_id: int) -> bool:
        """Return whether report_id is the newest durable report for the user."""
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    "SELECT id FROM partner_reports WHERE user_id = %s ORDER BY id DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    "SELECT id FROM partner_reports WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
        return bool(row and int(row["id"]) == report_id)

    def recent(self, user_id: int, limit: int = 10) -> list[SavedReport]:
        if self.database_url:
            with self._connect_postgres() as conn:
                rows = conn.execute(
                    """
                    SELECT id, user_id, partner_name, birth_date, emotional_language_title, created_at
                    FROM partner_reports
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                ).fetchall()
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT id, user_id, partner_name, birth_date, emotional_language_title, created_at
                    FROM partner_reports
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
        return [
            SavedReport(
                id=int(row["id"]),
                user_id=int(row["user_id"]),
                partner_name=str(row["partner_name"]),
                birth_date=str(row["birth_date"]),
                emotional_language_title=str(row["emotional_language_title"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def all_user_ids(self) -> list[int]:
        query = """
            SELECT user_id FROM bot_users
            UNION
            SELECT DISTINCT user_id FROM partner_reports
            ORDER BY user_id
            """
        if self.database_url:
            with self._connect_postgres() as conn:
                rows = conn.execute(query).fetchall()
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute(query).fetchall()
        return [int(row["user_id"]) for row in rows]

    def was_broadcast_sent(self, broadcast_key: str) -> bool:
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    "SELECT broadcast_key FROM broadcast_log WHERE broadcast_key = %s",
                    (broadcast_key,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    "SELECT broadcast_key FROM broadcast_log WHERE broadcast_key = ?",
                    (broadcast_key,),
                ).fetchone()
        return row is not None

    def mark_broadcast_sent(self, broadcast_key: str, total: int, success: int, failed: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        query = """
            INSERT INTO broadcast_log (broadcast_key, sent_at, total, success, failed)
            VALUES ({placeholders})
            ON CONFLICT(broadcast_key) DO UPDATE SET
                sent_at = excluded.sent_at,
                total = excluded.total,
                success = excluded.success,
                failed = excluded.failed
            """
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    query.format(placeholders="%s, %s, %s, %s, %s"),
                    (broadcast_key, now, total, success, failed),
                )
        else:
            with self._connect_sqlite() as conn:
                conn.execute(query.format(placeholders="?, ?, ?, ?, ?"), (broadcast_key, now, total, success, failed))

    def get_profile(self, user_id: int) -> dict[str, str]:
        self.register_user(user_id)
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT self_name, self_birth_date, partner_name, partner_birth_date
                    FROM user_profiles
                    WHERE user_id = %s
                    """,
                    (user_id,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT self_name, self_birth_date, partner_name, partner_birth_date
                    FROM user_profiles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()
        if row is None:
            return dict(DEFAULT_PROFILE)
        return {
            "self_name": str(row["self_name"] or ""),
            "self_birth_date": str(row["self_birth_date"] or ""),
            "partner_name": str(row["partner_name"] or ""),
            "partner_birth_date": str(row["partner_birth_date"] or ""),
        }

    def healthcheck(self) -> dict[str, Any]:
        """Return a small storage readiness payload for deployment health endpoints."""
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute("SELECT 1 AS ok").fetchone()
            return {"ok": bool(row and row["ok"] == 1), "storage": "postgres"}
        with self._connect_sqlite() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return {"ok": bool(row and row["ok"] == 1), "storage": "sqlite", "path": str(self.db_path)}

    def save_profile(self, user_id: int, profile: dict[str, Any]) -> dict[str, str]:
        self.register_user(user_id)
        clean = {key: str(profile.get(key, "") or "").strip()[:80] for key in DEFAULT_PROFILE}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        query = """
            INSERT INTO user_profiles (
                user_id, self_name, self_birth_date, partner_name, partner_birth_date, updated_at
            )
            VALUES ({placeholders})
            ON CONFLICT(user_id) DO UPDATE SET
                self_name = excluded.self_name,
                self_birth_date = excluded.self_birth_date,
                partner_name = excluded.partner_name,
                partner_birth_date = excluded.partner_birth_date,
                updated_at = excluded.updated_at
            """
        values = (
            user_id,
            clean["self_name"],
            clean["self_birth_date"],
            clean["partner_name"],
            clean["partner_birth_date"],
            now,
        )
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(query.format(placeholders="%s, %s, %s, %s, %s, %s"), values)
        else:
            with self._connect_sqlite() as conn:
                conn.execute(query.format(placeholders="?, ?, ?, ?, ?, ?"), values)
        return clean

    def track_event(self, user_id: int | None, event_name: str, properties: dict[str, Any] | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = json.dumps(properties or {}, ensure_ascii=False)
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    """
                    INSERT INTO analytics_events (user_id, event_name, event_json, created_at)
                    VALUES (%s, %s, %s::jsonb, %s)
                    """,
                    (user_id, event_name, payload, now),
                )
            return
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                INSERT INTO analytics_events (user_id, event_name, event_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, event_name, payload, now),
            )

    def grant_entitlement(self, user_id: int, product_key: str, report_id: int, payment_payload: str = "") -> None:
        self.register_user(user_id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        query = """
            INSERT INTO premium_entitlements (user_id, product_key, report_id, unlocked_at, payment_payload)
            VALUES ({placeholders})
            ON CONFLICT(user_id, product_key, report_id) DO UPDATE SET
                unlocked_at = excluded.unlocked_at,
                payment_payload = excluded.payment_payload
            """
        values = (user_id, product_key, report_id, now, payment_payload)
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(query.format(placeholders="%s, %s, %s, %s, %s"), values)
            return
        with self._connect_sqlite() as conn:
            conn.execute(query.format(placeholders="?, ?, ?, ?, ?"), values)

    def has_entitlement(self, user_id: int, product_key: str, report_id: int) -> bool:
        self.register_user(user_id)
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM premium_entitlements
                    WHERE user_id = %s AND product_key = %s AND report_id = %s
                    LIMIT 1
                    """,
                    (user_id, product_key, report_id),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM premium_entitlements
                    WHERE user_id = ? AND product_key = ? AND report_id = ?
                    LIMIT 1
                    """,
                    (user_id, product_key, report_id),
                ).fetchone()
        return row is not None

    def list_entitlements(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """List a buyer's durable purchases for self-service recovery."""
        self.register_user(user_id)
        safe_limit = max(1, min(int(limit), 200))
        if self.database_url:
            with self._connect_postgres() as conn:
                rows = conn.execute(
                    """
                    SELECT product_key, report_id, unlocked_at, payment_payload
                    FROM premium_entitlements
                    WHERE user_id = %s
                    ORDER BY unlocked_at DESC
                    LIMIT %s
                    """,
                    (user_id, safe_limit),
                ).fetchall()
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT product_key, report_id, unlocked_at, payment_payload
                    FROM premium_entitlements
                    WHERE user_id = ?
                    ORDER BY unlocked_at DESC
                    LIMIT ?
                    """,
                    (user_id, safe_limit),
                ).fetchall()
        return [
            {
                "product_key": str(row["product_key"] or ""),
                "report_id": int(row["report_id"]),
                "unlocked_at": str(row["unlocked_at"] or ""),
                "payment_payload": str(row["payment_payload"] or ""),
            }
            for row in rows
        ]


def format_history(items: list[SavedReport]) -> str:
    if not items:
        return "История пока пустая. Нажми /partner и разбери первого человека. Всё великое начинается с формы ввода, как ни печально."
    lines = ["🗂 История разборов", ""]
    for item in items:
        lines.append(f"#{item.id} — {item.partner_name}, {item.birth_date}")
        lines.append(f"{item.emotional_language_title}")
        lines.append("")
    return "\n".join(lines).strip()
