from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SavedReport:
    id: int
    user_id: int
    partner_name: str
    birth_date: str
    emotional_language_title: str
    created_at: str


class ReportsStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
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

    def add(self, user_id: int, report: object) -> int:
        payload = report.to_dict()  # PartnerReport-like object. Keep storage decoupled.
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
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

    def recent(self, user_id: int, limit: int = 10) -> list[SavedReport]:
        with self._connect() as conn:
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


def format_history(items: list[SavedReport]) -> str:
    if not items:
        return "История пока пустая. Нажми /partner и разбери первого человека. Всё великое начинается с формы ввода, как ни печально."
    lines = ["🗂 История разборов", ""]
    for item in items:
        lines.append(f"#{item.id} — {item.partner_name}, {item.birth_date}")
        lines.append(f"{item.emotional_language_title}")
        lines.append("")
    return "\n".join(lines).strip()
