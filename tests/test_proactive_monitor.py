"""
Unit tests for Proactive Network Monitor.
"""

import unittest
from unittest.mock import MagicMock, patch
from config.settings import DeviceConfig, settings
from core.monitor import ProactiveMonitor
from mikrotik.base import OperationResult, ResourceInfo


class TestProactiveMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = ProactiveMonitor()

    def test_alert_on_device_down(self):
        # Setup mock client that returns connection failure
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=False, message="Connection Refused", device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        # Set initial status as ONLINE
        self.monitor.device_states["test_router"] = {
            "status": "ONLINE",
            "high_cpu": False,
            "fail_count": 0,
            "last_check": 0.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client):

            alerts = self.monitor.check_devices()

            # Should produce 1 alert message
            self.assertEqual(len(alerts), 1)
            self.assertIn("ROUTER DOWN", alerts[0])
            self.assertEqual(self.monitor.device_states["test_router"]["status"], "OFFLINE")

    def test_recovery_alert_when_back_online(self):
        # Setup mock client that returns success
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=True, message="Connected OK", device="TestRouter", latency_ms=4.5
        )
        mock_client.get_resource.return_value = OperationResult(
            success=True, data=ResourceInfo(cpu_load=20, uptime="2d"), device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        # Set initial status as OFFLINE
        self.monitor.device_states["test_router"] = {
            "status": "OFFLINE",
            "high_cpu": False,
            "fail_count": 2,
            "last_check": 0.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client):

            alerts = self.monitor.check_devices()

            # Should produce 1 recovery alert message
            self.assertEqual(len(alerts), 1)
            self.assertIn("ROUTER RECOVERED", alerts[0])
            self.assertEqual(self.monitor.device_states["test_router"]["status"], "ONLINE")

    def test_high_cpu_warning(self):
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=True, message="Connected OK", device="TestRouter", latency_ms=2.0
        )
        # 95% CPU load (> 90% threshold)
        mock_client.get_resource.return_value = OperationResult(
            success=True, data=ResourceInfo(cpu_load=95, uptime="5d"), device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        self.monitor.device_states["test_router"] = {
            "status": "ONLINE",
            "high_cpu": False,
            "fail_count": 0,
            "last_check": 0.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client):

            alerts = self.monitor.check_devices()

            self.assertEqual(len(alerts), 1)
            self.assertIn("BEBAN CPU TINGGI", alerts[0])
            self.assertTrue(self.monitor.device_states["test_router"]["high_cpu"])

    def test_high_cpu_hysteresis_deadband(self):
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=True, message="Connected OK", device="TestRouter", latency_ms=2.0
        )
        # 82% CPU load: below 90% threshold, but above 75% recovery threshold
        mock_client.get_resource.return_value = OperationResult(
            success=True, data=ResourceInfo(cpu_load=82, uptime="5d"), device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        # Already in high_cpu state
        self.monitor.device_states["test_router"] = {
            "status": "ONLINE",
            "high_cpu": True,
            "fail_count": 0,
            "last_check": 0.0,
            "last_cpu_alert": 1000.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client), \
             patch("time.time", return_value=1100.0):

            alerts = self.monitor.check_devices()

            # No alert should be generated, and state must remain high_cpu = True (no flapping!)
            self.assertEqual(len(alerts), 0)
            self.assertTrue(self.monitor.device_states["test_router"]["high_cpu"])

    def test_high_cpu_cooldown_suppression(self):
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=True, message="Connected OK", device="TestRouter", latency_ms=2.0
        )
        # 95% CPU load (> 90%)
        mock_client.get_resource.return_value = OperationResult(
            success=True, data=ResourceInfo(cpu_load=95, uptime="5d"), device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        # Alerted 60 seconds ago (cooldown is 900s)
        self.monitor.device_states["test_router"] = {
            "status": "ONLINE",
            "high_cpu": True,
            "fail_count": 0,
            "last_check": 0.0,
            "last_cpu_alert": 1000.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client), \
             patch("time.time", return_value=1060.0):

            alerts = self.monitor.check_devices()

            # Should be suppressed by cooldown
            self.assertEqual(len(alerts), 0)

    def test_high_cpu_recovery(self):
        mock_client = MagicMock()
        mock_client.test_connection.return_value = OperationResult(
            success=True, message="Connected OK", device="TestRouter", latency_ms=2.0
        )
        # 30% CPU load: safely below 75% recovery threshold
        mock_client.get_resource.return_value = OperationResult(
            success=True, data=ResourceInfo(cpu_load=30, uptime="5d"), device="TestRouter"
        )

        test_device = DeviceConfig({
            "id": "test_router",
            "name": "Test Router",
            "host": "192.168.1.1",
            "port": 8728,
            "protocol": "api",
        })

        # Previously high_cpu
        self.monitor.device_states["test_router"] = {
            "status": "ONLINE",
            "high_cpu": True,
            "fail_count": 0,
            "last_check": 0.0,
            "last_cpu_alert": 1000.0,
        }

        with patch.object(settings, "devices", [test_device]), \
             patch("core.monitor.device_manager.get_client", return_value=mock_client), \
             patch("time.time", return_value=1200.0):

            alerts = self.monitor.check_devices()

            # Recovery alert should be emitted
            self.assertEqual(len(alerts), 1)
            self.assertIn("BEBAN CPU KEMBALI NORMAL", alerts[0])
            self.assertFalse(self.monitor.device_states["test_router"]["high_cpu"])


if __name__ == "__main__":
    unittest.main()

