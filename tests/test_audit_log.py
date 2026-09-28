"""
Unit tests for Audit Logger (PRD Section 21 & 22).
"""

import os
import unittest
from pathlib import Path
from core.audit import AuditLogger


class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.test_db = Path("data/test_audit.db")
        self.test_jsonl = Path("logs/test_audit.jsonl")
        if self.test_db.exists():
            self.test_db.unlink()
        if self.test_jsonl.exists():
            self.test_jsonl.unlink()
        self.logger = AuditLogger(db_path=self.test_db, jsonl_path=self.test_jsonl)

    def tearDown(self):
        if self.test_db.exists():
            try:
                self.test_db.unlink()
            except Exception:
                pass
        if self.test_jsonl.exists():
            try:
                self.test_jsonl.unlink()
            except Exception:
                pass

    def test_log_and_retrieve(self):
        self.logger.log_event(
            telegram_user_id=123456,
            telegram_user_name="admin_test",
            user_prompt="Cek kondisi router kantor utama",
            target_device="Kantor Utama",
            action_category="MONITOR",
            action_name="get_resource",
            confirmation_status="NONE",
            result_status="SUCCESS",
            details={"cpu": 14},
            latency_ms=12.5,
        )

        logs = self.logger.get_recent_logs(limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["telegram_user_id"], 123456)
        self.assertEqual(logs[0]["action_name"], "get_resource")
        self.assertEqual(logs[0]["target_device"], "Kantor Utama")

        # Verify JSONL file exists and contains entry
        self.assertTrue(self.test_jsonl.exists())
        with open(self.test_jsonl, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("admin_test", content)
            self.assertIn("Kantor Utama", content)


if __name__ == "__main__":
    unittest.main()
