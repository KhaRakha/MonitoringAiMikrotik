"""
Unit tests for Security and RBAC modules (PRD Section 16 & 17).
"""

import unittest
from core.security import security_manager


class TestSecurityManager(unittest.TestCase):
    def test_dangerous_detection(self):
        dangerous_queries = [
            "Tolong reset-configuration router ini",
            "Reset MikroTik ke setelan pabrik",
            "Lakukan factory reset sekarang",
            "reboot router kantor",
            "hapus semua konfigurasi jaringan",
        ]
        for q in dangerous_queries:
            is_dang, warning = security_manager.is_dangerous(q)
            self.assertTrue(is_dang, f"Query '{q}' should be flagged as dangerous")
            self.assertIn("⚠️ OPERASI BERISIKO TINGGI", warning)

    def test_safe_queries(self):
        safe_queries = [
            "Coba cek kondisi MikroTik kantor utama.",
            "Kenapa internet kantor terasa lambat?",
            "Cek user hotspot yang sedang aktif.",
            "Ping ke 8.8.8.8",
        ]
        for q in safe_queries:
            is_dang, _ = security_manager.is_dangerous(q)
            self.assertFalse(is_dang, f"Query '{q}' should NOT be flagged as dangerous")

    def test_classify_permission(self):
        self.assertEqual(security_manager.classify_permission("get_resource"), "READ")
        self.assertEqual(security_manager.classify_permission("get_interface"), "READ")
        self.assertEqual(security_manager.classify_permission("ping"), "READ")
        self.assertEqual(security_manager.classify_permission("create_hotspot_user"), "WRITE")
        self.assertEqual(security_manager.classify_permission("delete_hotspot_user"), "WRITE")
        self.assertEqual(security_manager.classify_permission("set_interface_state"), "WRITE")
        self.assertEqual(security_manager.classify_permission("reset-configuration"), "DANGEROUS")

    def test_redact_secrets(self):
        text = "Login with password=supersecret123 and api_key=xyz8899"
        cleaned = security_manager.redact_secrets(text)
        self.assertNotIn("supersecret123", cleaned)
        self.assertNotIn("xyz8899", cleaned)
        self.assertIn("[REDACTED]", cleaned)

        # Test quoted password redaction
        quoted_text = 'router configuration password="magang@2026" and token: "abc12345"'
        quoted_cleaned = security_manager.redact_secrets(quoted_text)
        self.assertNotIn("magang@2026", quoted_cleaned)
        self.assertIn("[REDACTED]", quoted_cleaned)

    def test_device_matching_word_boundary(self):
        """Ensure device alias 'lab' does not match within words like 'lambat'."""
        from config.settings import settings
        # 'lambat' should NOT match lab_pti
        lab_dev = next((d for d in settings.devices if d.id == "lab_pti"), None)
        if lab_dev:
            self.assertFalse(lab_dev.matches("Kenapa internet terasa lambat?"))
            self.assertTrue(lab_dev.matches("Cek kondisi router lab"))


    def test_rbac_roles(self):
        from config.settings import settings
        # Backup original settings
        orig_admin = list(settings.admin_telegram_ids)
        orig_viewer = list(settings.viewer_telegram_ids)
        orig_allowed = list(settings.allowed_telegram_ids)

        try:
            settings.admin_telegram_ids = [11111]
            settings.viewer_telegram_ids = [22222]
            settings.allowed_telegram_ids = [11111, 22222]

            # Test Admin
            self.assertEqual(security_manager.get_user_role(11111), "ADMIN")
            self.assertTrue(security_manager.can_user_write(11111))

            # Test Viewer
            self.assertEqual(security_manager.get_user_role(22222), "VIEWER")
            self.assertFalse(security_manager.can_user_write(22222))

            # Test Unauthorized
            self.assertEqual(security_manager.get_user_role(99999), "UNAUTHORIZED")
            self.assertFalse(security_manager.can_user_write(99999))
        finally:
            settings.admin_telegram_ids = orig_admin
            settings.viewer_telegram_ids = orig_viewer
            settings.allowed_telegram_ids = orig_allowed


if __name__ == "__main__":
    unittest.main()
