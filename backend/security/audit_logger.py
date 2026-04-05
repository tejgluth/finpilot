"""
Append-only audit log written to both SQLite and a flat file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import sqlite3

from backend.config import settings


class AuditLogger:
    @staticmethod
    def log(actor: str, event_type: str, data: dict) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "event_type": event_type,
            **data,
        }
        line = json.dumps(entry)
        try:
            Path(settings.audit_log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(settings.audit_log_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass

        try:
            db_path = str(settings.db_path)
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO audit_log (timestamp, actor, event_type, data) VALUES (?, ?, ?, ?)",
                (entry["timestamp"], actor, event_type, line),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def read(limit: int = 100) -> list[dict]:
        try:
            conn = sqlite3.connect(str(settings.db_path))
            rows = conn.execute(
                "SELECT data FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [json.loads(row[0]) for row in rows]
        except Exception:
            return []
