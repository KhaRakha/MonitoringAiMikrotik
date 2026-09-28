"""
Audit Logging and Trail Module (PRD Section 21 & 22).
Persists administrative activity to SQLite database and JSON Lines audit files.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config.settings import settings


class AuditLogger:
    def __init__(self, db_path: Optional[Path] = None, jsonl_path: Optional[Path] = None):
        self.db_path = db_path or settings.database_path
        self.jsonl_path = jsonl_path or settings.log_file_path
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    telegram_user_id INTEGER,
                    telegram_user_name TEXT,
                    user_prompt TEXT,
                    target_device TEXT,
                    action_category TEXT,
                    action_name TEXT,
                    confirmation_status TEXT,
                    result_status TEXT,
                    details TEXT,
                    latency_ms REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(telegram_user_id)")
            conn.commit()

    def log_event(
        self,
        telegram_user_id: int,
        telegram_user_name: str,
        user_prompt: str,
        target_device: str,
        action_category: str,
        action_name: str,
        confirmation_status: str = "NONE",
        result_status: str = "SUCCESS",
        details: Optional[Any] = None,
        latency_ms: float = 0.0,
    ) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details_str = json.dumps(details, default=str) if details is not None else ""

        # 1. Write to SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        timestamp, telegram_user_id, telegram_user_name,
                        user_prompt, target_device, action_category,
                        action_name, confirmation_status, result_status,
                        details, latency_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ts,
                        telegram_user_id,
                        telegram_user_name,
                        user_prompt,
                        target_device,
                        action_category,
                        action_name,
                        confirmation_status,
                        result_status,
                        details_str,
                        round(latency_ms, 2),
                    ),
                )
                conn.commit()
        except Exception as e:
            print(f"[AuditLogger] SQLite Error: {e}")

        # 2. Write to JSONL
        try:
            record = {
                "timestamp": ts,
                "user_id": telegram_user_id,
                "username": telegram_user_name,
                "prompt": user_prompt,
                "device": target_device,
                "category": action_category,
                "action": action_name,
                "confirmation": confirmation_status,
                "result": result_status,
                "latency_ms": round(latency_ms, 2),
            }
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AuditLogger] JSONL Error: {e}")

    def get_recent_logs(self, limit: int = 10, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM audit_logs WHERE telegram_user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                )
            else:
                cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


audit_logger = AuditLogger()
