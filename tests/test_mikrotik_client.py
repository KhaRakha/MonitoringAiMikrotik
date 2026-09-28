"""
Unit tests for MikroTik clients (Mock, REST, RouterOS API).
"""

import unittest
from mikrotik.mock_client import MockMikrotikClient


class TestMockMikrotikClient(unittest.TestCase):
    def setUp(self):
        self.client = MockMikrotikClient()

    def test_connection(self):
        res = self.client.test_connection()
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("status"), "online")

    def test_get_resource(self):
        res = self.client.get_resource()
        self.assertTrue(res.success)
        data = res.data
        self.assertIn("cpu_load", data)
        self.assertIn("memory_usage_percent", data)
        self.assertIn("uptime", data)
        self.assertIn("version", data)

    def test_get_interfaces(self):
        res = self.client.get_interfaces()
        self.assertTrue(res.success)
        ifaces = res.data
        self.assertGreaterEqual(len(ifaces), 3)
        wan = next((i for i in ifaces if "WAN" in i["name"]), None)
        self.assertIsNotNone(wan)
        self.assertTrue(wan["running"])

    def test_ping(self):
        res = self.client.ping("8.8.8.8", count=4)
        self.assertTrue(res.success)
        self.assertEqual(res.data["sent"], 4)
        self.assertEqual(res.data["packet_loss_percent"], 0.0)

    def test_hotspot_crud(self):
        # 1. Create user
        create_res = self.client.create_hotspot_user(name="UserTest1", limit_uptime="2h")
        self.assertTrue(create_res.success)

        # 2. Verify user exists
        users_res = self.client.get_hotspot_users()
        user_names = [u["name"] for u in users_res.data]
        self.assertIn("UserTest1", user_names)

        # 3. Duplicate creation should fail
        dup_res = self.client.create_hotspot_user(name="UserTest1")
        self.assertFalse(dup_res.success)

        # 4. Delete user
        del_res = self.client.delete_hotspot_user(name="UserTest1")
        self.assertTrue(del_res.success)

        # 5. Verify user is removed
        users_res2 = self.client.get_hotspot_users()
        user_names2 = [u["name"] for u in users_res2.data]
        self.assertNotIn("UserTest1", user_names2)

    def test_interface_state(self):
        res = self.client.set_interface_state("ether5", enabled=True)
        self.assertTrue(res.success)
        self.assertFalse(res.data["disabled"])

        res2 = self.client.set_interface_state("ether5", enabled=False)
        self.assertTrue(res2.success)
        self.assertTrue(res2.data["disabled"])


if __name__ == "__main__":
    unittest.main()
