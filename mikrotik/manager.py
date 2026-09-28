"""
MikroTik Device Manager.
Handles multi-device inventory, client pooling, name resolution, and fallback mechanisms.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple
from config.settings import DeviceConfig, settings
from mikrotik.base import BaseMikrotikClient, OperationResult
from mikrotik.mock_client import MockMikrotikClient
from mikrotik.rest_client import MikrotikRestClient
from mikrotik.ros_api_client import MikrotikRosApiClient
from mikrotik.ssh_client import MikrotikSshClient

logger = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self):
        self._clients: Dict[str, BaseMikrotikClient] = {}
        self._status_cache: Dict[str, Tuple[bool, float]] = {}
        self.mock_client = MockMikrotikClient()

    def _create_client(self, dev: DeviceConfig) -> BaseMikrotikClient:
        proto = dev.protocol.lower()
        if proto == "mock":
            client = MockMikrotikClient(
                host=dev.host,
                port=dev.port,
                username=dev.username,
                password=dev.password,
            )
        elif proto == "rest":
            client = MikrotikRestClient(
                host=dev.host,
                port=dev.port or (443 if dev.use_ssl else 80),
                username=dev.username,
                password=dev.password,
                use_ssl=dev.use_ssl,
            )
        elif proto == "api":
            client = MikrotikRosApiClient(
                host=dev.host,
                port=dev.port or (8729 if dev.use_ssl else 8728),
                username=dev.username,
                password=dev.password,
                use_ssl=dev.use_ssl,
            )
        elif proto == "ssh":
            client = MikrotikSshClient(
                host=dev.host,
                port=dev.port or 22,
                username=dev.username,
                password=dev.password,
            )
        else:
            client = MockMikrotikClient()

        client.device_name = dev.name
        return client

    def get_client(self, query: Optional[str] = None) -> BaseMikrotikClient:
        """Resolve device by query name/alias and return appropriate client."""
        dev = settings.find_device(query or "")
        if not dev:
            logger.warning("No device matched '%s', using mock client.", query)
            return self.mock_client

        if dev.id not in self._clients:
            self._clients[dev.id] = self._create_client(dev)

        client = self._clients[dev.id]

        # Auto fallback to mock client if physical router is offline and fallback is allowed
        if dev.protocol != "mock" and settings.enable_mock_fallback:
            now = time.time()
            cached_status = self._status_cache.get(dev.id)
            if cached_status and (now - cached_status[1]) < 15.0:
                is_online = cached_status[0]
            else:
                test = client.test_connection()
                is_online = test.success
                self._status_cache[dev.id] = (is_online, now)

            if not is_online:
                logger.info(
                    "Device '%s' (%s) unreachable. Using MockMikrotikClient fallback (enable_mock_fallback=True).",
                    dev.name,
                    dev.host,
                )
                fallback = MockMikrotikClient()
                fallback.device_name = f"{dev.name} [Simulasi Offline]"
                fallback.is_fallback_mock = True
                fallback.real_device_name = dev.name
                fallback.real_device_host = dev.host
                return fallback

        return client

    def list_devices(self) -> List[Dict[str, Any]]:
        """Return list of all configured devices and their quick status."""
        results = []
        for dev in settings.devices:
            if dev.id not in self._clients:
                self._clients[dev.id] = self._create_client(dev)
            client = self._clients[dev.id]
            status_res = client.test_connection()
            self._status_cache[dev.id] = (status_res.success, time.time())
            results.append({
                "id": dev.id,
                "name": dev.name,
                "host": dev.host,
                "port": dev.port,
                "protocol": dev.protocol,
                "is_default": dev.is_default,
                "description": dev.description,
                "online": status_res.success,
                "status_message": status_res.message,
                "latency_ms": status_res.latency_ms,
            })
        return results


device_manager = DeviceManager()
