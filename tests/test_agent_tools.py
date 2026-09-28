"""
Integration tests for Hermes AI Agent reasoning and tool execution (PRD Section 24, 25, 26).
"""

import unittest
from core.agent import hermes_agent
from mikrotik.tools import (
    connect_mikrotik,
    get_interface,
    get_resource,
    ping,
)


class TestAgentScenarios(unittest.TestCase):
    def setUp(self):
        self.user_id = 777123
        self.username = "test_engineer"
        from config.settings import settings
        if self.user_id not in settings.admin_telegram_ids:
            settings.admin_telegram_ids.append(self.user_id)
        if self.user_id not in settings.allowed_telegram_ids:
            settings.allowed_telegram_ids.append(self.user_id)
        # Ensure offline deterministic heuristic reasoning for unit test scenarios
        self._orig_google_key = hermes_agent.google_api_key
        self._orig_openai_key = hermes_agent.openai_api_key
        hermes_agent.google_api_key = ""
        hermes_agent.openai_api_key = ""

    def tearDown(self):
        hermes_agent.google_api_key = self._orig_google_key
        hermes_agent.openai_api_key = self._orig_openai_key

    def test_scenario_1_monitoring(self):
        """PRD Section 24: Coba cek kondisi MikroTik kantor utama."""
        query = "Coba cek kondisi MikroTik kantor utama."
        res = hermes_agent.process_message(self.user_id, self.username, query)
        reply = res["reply"]

        self.assertFalse(res["action_required"])
        self.assertIn("MikroTik", reply)
        self.assertIn("CPU", reply)
        self.assertIn("RAM", reply)
        self.assertIn("Uptime", reply)
        self.assertIn("Kesimpulan", reply)

    def test_scenario_2_troubleshooting(self):
        """PRD Section 25: Internet kantor terasa lambat, coba cari penyebabnya."""
        query = "Internet kantor terasa lambat, coba cari penyebabnya."
        res = hermes_agent.process_message(self.user_id, self.username, query)
        reply = res["reply"]

        self.assertFalse(res["action_required"])
        self.assertIn("Hasil Pemeriksaan Diagnostik", reply)
        self.assertIn("CPU", reply)
        self.assertIn("WAN", reply)
        self.assertIn("Ping", reply)
        self.assertIn("Kesimpulan Analisis", reply)

    def test_scenario_3_configuration_flow(self):
        """PRD Section 26: Buat user hotspot Tamu123 untuk tamu, aktif satu hari."""
        query = "Buatkan user hotspot untuk tamu bernama Tamu123, aktif satu hari"
        res = hermes_agent.process_message(self.user_id, self.username, query)

        # 1. Must require confirmation
        self.assertTrue(res["action_required"])
        self.assertIsNotNone(res["pending_action"])
        self.assertIn("Konfirmasi", res["reply"])
        self.assertIn("Tamu123", res["reply"])

        # 2. User confirms with "Ya"
        confirm_res = hermes_agent.process_message(self.user_id, self.username, "Ya")
        self.assertFalse(confirm_res["action_required"])
        self.assertIn("berhasil dibuat", confirm_res["reply"])

    def test_dangerous_operation_rejection(self):
        """PRD Section 16: Reset MikroTik must be blocked."""
        query = "Tolong lakukan factory reset MikroTik kantor utama"
        res = hermes_agent.process_message(self.user_id, self.username, query)

        self.assertFalse(res["action_required"])
        self.assertIn("OPERASI BERISIKO TINGGI DITOLAK", res["reply"])
        self.assertIn("TIDAK TERSEDIA melalui AI Bot", res["reply"])


    def test_viewer_write_restriction(self):
        """RBAC: Viewer user cannot create or delete hotspot users."""
        from config.settings import settings
        viewer_id = 999123
        if viewer_id not in settings.viewer_telegram_ids:
            settings.viewer_telegram_ids.append(viewer_id)
        if viewer_id not in settings.allowed_telegram_ids:
            settings.allowed_telegram_ids.append(viewer_id)
        if viewer_id in settings.admin_telegram_ids:
            settings.admin_telegram_ids.remove(viewer_id)

        query = "Buatkan user hotspot untuk tamu bernama Tamu999, aktif satu hari"
        res = hermes_agent.process_message(viewer_id, "viewer_user", query)

        self.assertFalse(res["action_required"])
        self.assertIsNone(res["pending_action"])
        self.assertIn("Viewer (Read-Only)", res["reply"])


    def test_flexible_specific_queries(self):
        """Flexible responses: user gets direct answers without rigid code templates."""
        # 1. Specific CPU check
        res_cpu = hermes_agent.process_message(self.user_id, self.username, "Berapa beban CPU sekarang?")
        self.assertIn("CPU", res_cpu["reply"])
        self.assertNotIn("WAN Status", res_cpu["reply"])  # Must not dump entire WAN/traffic if only asked for CPU

        # 2. Specific Uptime check
        res_up = hermes_agent.process_message(self.user_id, self.username, "Berapa uptime router?")
        self.assertIn("Uptime", res_up["reply"])

        # 3. Conversational greeting
        res_greet = hermes_agent.process_message(self.user_id, self.username, "Halo selamat pagi")
        self.assertIn("Halo", res_greet["reply"])

        # 4. Thank you
        res_thanks = hermes_agent.process_message(self.user_id, self.username, "Terima kasih banyak")
        self.assertIn("Sama-sama", res_thanks["reply"])

    def test_router_type_hardware_info(self):
        """Case 1: Hardware & router info (identity, model, version, architecture)."""
        queries = [
            "kamu itu router type apa",
            "router type apa?",
            "MikroTik ini tipe apa?",
            "model router apa?",
        ]
        for q in queries:
            res = hermes_agent.process_message(self.user_id, self.username, q)
            reply = res["reply"]
            self.assertIn("Informasi Sistem & Perangkat", reply, f"Failed for query: {q}")
            self.assertIn("Model / Tipe", reply, f"Failed for query: {q}")
            self.assertIn("Versi RouterOS", reply, f"Failed for query: {q}")
            self.assertIn("Arsitektur CPU", reply, f"Failed for query: {q}")
            self.assertNotIn("Daftar Alamat IP Interface", reply, f"Should not dump interface IPs for: {q}")
            self.assertNotIn("Tabel Routing IP", reply, f"Should not dump routes for: {q}")

    def test_wan_ip_classification(self):
        """Case 2: WAN interface, gateway, and verified IP classification (RFC 1918 / CGNAT / Public)."""
        queries = [
            "Cek ip wan kamu",
            "ip wan apa",
            "berapa ip publik router",
        ]
        for q in queries:
            res = hermes_agent.process_message(self.user_id, self.username, q)
            reply = res["reply"]
            self.assertIn("Informasi Koneksi WAN & Gateway Internet", reply, f"Failed for query: {q}")
            self.assertIn("Interface WAN", reply, f"Failed for query: {q}")
            self.assertIn("Alamat IP WAN", reply, f"Failed for query: {q}")
            self.assertIn("Klasifikasi Alamat", reply, f"Failed for query: {q}")
            self.assertNotIn("Daftar Alamat IP Interface", reply, f"Should not be full interface IP list for: {q}")

    def test_routing_table_queries(self):
        """Case 3: Active routing table (/ip/route) destination, gateway, distance, status."""
        queries = [
            "Cek rute kamu apa aja",
            "cek route",
            "lihat routing",
            "routing table apa saja",
            "rute yang aktif apa?",
        ]
        for q in queries:
            res = hermes_agent.process_message(self.user_id, self.username, q)
            reply = res["reply"]
            self.assertIn("Tabel Routing IP", reply, f"Failed for query: {q}")
            self.assertIn("Total Rute Terpasang", reply, f"Failed for query: {q}")
            self.assertIn("Gateway", reply, f"Failed for query: {q}")

    def test_ping_factual_reporting(self):
        """Case 4: Factual ping statistics without exaggerated gaming/VoIP claims."""
        queries = [
            "Ping 1.1.1.1",
            "tes koneksi ke 8.8.8.8",
            "apakah 1.1.1.1 bisa dijangkau?",
        ]
        for q in queries:
            res = hermes_agent.process_message(self.user_id, self.username, q)
            reply = res["reply"]
            self.assertIn("Hasil Pengujian Ping", reply, f"Failed for query: {q}")
            self.assertIn("Paket Dikirim", reply, f"Failed for query: {q}")
            self.assertIn("Paket Diterima", reply, f"Failed for query: {q}")
            self.assertIn("Packet Loss", reply, f"Failed for query: {q}")
            # Ensure no speculative/exaggerated statements based on small ping samples
            self.assertNotIn("gaming", reply.lower(), f"Speculation found for query: {q}")
            self.assertNotIn("voip", reply.lower(), f"Speculation found for query: {q}")

    def test_traceroute_queries(self):
        """Case 5: RouterOS traceroute hop list, RTT, destination status without word collisions."""
        queries = [
            "traceroute 8.8.8.8",
            "trace jalur ke 8.8.8.8",
            "lihat hop menuju 8.8.8.8",
        ]
        for q in queries:
            res = hermes_agent.process_message(self.user_id, self.username, q)
            reply = res["reply"]
            self.assertIn("Hasil Traceroute", reply, f"Failed for query: {q}")
            self.assertIn("Hop", reply, f"Failed for query: {q}")
            self.assertNotIn("Panduan Penggunaan Bot", reply, f"Word collision triggered help for: {q}")

    def test_interface_ip_queries(self):
        """Interface IP query must return all interface IPs cleanly."""
        res = hermes_agent.process_message(self.user_id, self.username, "Cek daftar ip address")
        reply = res["reply"]
        self.assertIn("Daftar Alamat IP Interface", reply)
        self.assertIn("Total IP Terpasang", reply)


if __name__ == "__main__":
    unittest.main()
