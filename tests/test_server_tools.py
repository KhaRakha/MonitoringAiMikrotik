"""
Unit tests for universal server & port tools.
"""

import socket
import unittest
from mikrotik.tools import check_server_port, ping_host


class TestServerTools(unittest.TestCase):
    def test_check_server_port_open(self):
        # Bind a temporary local server socket to test port detection
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        try:
            res = check_server_port(host="127.0.0.1", port=port, timeout=1.0)
            self.assertTrue(res["success"])
            self.assertEqual(res["data"]["status"], "OPEN")
            self.assertEqual(res["data"]["port"], port)
        finally:
            server_sock.close()

    def test_check_server_port_closed(self):
        # Find a port that is guaranteed closed
        res = check_server_port(host="127.0.0.1", port=65432, timeout=0.2)
        self.assertFalse(res["success"])
        self.assertEqual(res["data"]["status"], "CLOSED_OR_FILTERED")

    def test_ping_host(self):
        # Ping localhost or default target
        res = ping_host(host="127.0.0.1", count=2)
        self.assertIn("success", res)


if __name__ == "__main__":
    unittest.main()
