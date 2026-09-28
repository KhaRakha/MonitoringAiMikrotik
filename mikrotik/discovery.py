"""
MikroTik Device Discovery Module (PRD Section 12).
Scans local networks to detect and identify active MikroTik routers.
"""

from __future__ import annotations

import concurrent.futures
import ipaddress
import re
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from config.settings import CONFIG_DIR, DeviceConfig, settings


class DeviceDiscovery:
    def __init__(self, ports: Optional[List[int]] = None, timeout: float = 0.5):
        self.ports = ports or [8291, 8728, 80, 443, 22]
        self.timeout = timeout

    def check_host(self, ip_str: str) -> Optional[Dict[str, Any]]:
        open_ports = []
        for port in self.ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                res = sock.connect_ex((ip_str, port))
                sock.close()
                if res == 0:
                    open_ports.append(port)
            except Exception:
                pass

        if open_ports:
            # Check if Winbox (8291) or RouterOS API (8728) is open
            is_likely_mikrotik = (8291 in open_ports) or (8728 in open_ports)
            return {
                "ip": ip_str,
                "open_ports": open_ports,
                "is_mikrotik": is_likely_mikrotik,
                "suggested_protocol": "rest" if (80 in open_ports or 443 in open_ports) else ("api" if 8728 in open_ports else "winbox_only"),
            }
        return None

    def scan_subnet(self, subnet_cidr: str = "10.20.33.0/24", max_hosts: int = 64) -> List[Dict[str, Any]]:
        discovered = []
        try:
            net = ipaddress.ip_network(subnet_cidr, strict=False)
            hosts = [str(ip) for ip in net.hosts()][:max_hosts]
        except Exception:
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(self.check_host, ip): ip for ip in hosts}
            for future in concurrent.futures.as_completed(future_to_ip):
                res = future.result()
                if res:
                    discovered.append(res)

        return sorted(discovered, key=lambda x: x["ip"])

    def register_device(
        self,
        name: str,
        host: str,
        protocol: str = "api",
        port: int = 0,
        username: str = "admin",
        password: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """Register a new router into config/devices.yaml and update runtime settings."""
        proto = protocol.lower().strip() if protocol else "api"
        if proto not in ("api", "rest", "ssh", "mock"):
            proto = "api"

        port_val = int(port) if port else 0
        if port_val <= 0:
            if proto == "api":
                port_val = 8728
            elif proto == "ssh":
                port_val = 22
            elif proto == "rest":
                port_val = 80
            else:
                port_val = 8728

        devices_file = CONFIG_DIR / "devices.yaml"
        if not devices_file.exists():
            data = {"devices": []}
        else:
            with open(devices_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {"devices": []}

        # Check if already exists
        for dev in data.get("devices", []):
            if dev.get("host") == host:
                return {
                    "success": False,
                    "message": f"Perangkat dengan IP {host} sudah terdaftar sebelumnya ({dev.get('name')}).",
                }
            if dev.get("name", "").lower() == name.lower():
                return {
                    "success": False,
                    "message": f"Perangkat dengan nama '{name}' sudah terdaftar dalam inventaris.",
                }

        device_id = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower().strip())
        new_entry = {
            "id": device_id,
            "name": name,
            "aliases": [name.lower(), device_id],
            "host": host,
            "port": port_val,
            "protocol": proto,
            "use_ssl": False,
            "username": username,
            "password": password,
            "is_default": False,
            "description": description or f"Router MikroTik {name} ({host})",
        }

        data.setdefault("devices", []).append(new_entry)
        with open(devices_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # Refresh runtime settings
        settings.devices.append(DeviceConfig(new_entry))
        return {
            "success": True,
            "message": f"Perangkat '{name}' ({host}:{port_val} [{proto.upper()}]) berhasil didaftarkan.",
            "data": new_entry,
        }

    def remove_device(self, name_or_id: str) -> Dict[str, Any]:
        """Remove a router from config/devices.yaml and runtime settings."""
        devices_file = CONFIG_DIR / "devices.yaml"
        if not devices_file.exists():
            return {"success": False, "message": "File devices.yaml tidak ditemukan."}

        with open(devices_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {"devices": []}

        target_dev = None
        remaining = []
        clean_target = name_or_id.lower().strip()
        for dev in data.get("devices", []):
            aliases = [a.lower() for a in dev.get("aliases", [])]
            if (
                dev.get("id", "").lower() == clean_target
                or dev.get("name", "").lower() == clean_target
                or clean_target in aliases
                or dev.get("host", "") == clean_target
            ):
                target_dev = dev
            else:
                remaining.append(dev)

        if not target_dev:
            return {"success": False, "message": f"Perangkat '{name_or_id}' tidak ditemukan dalam inventaris."}

        data["devices"] = remaining
        with open(devices_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # Refresh runtime settings
        settings.devices = [d for d in settings.devices if d.id != target_dev.get("id")]
        return {
            "success": True,
            "message": f"Perangkat '{target_dev.get('name')}' ({target_dev.get('host')}) berhasil dihapus dari inventaris.",
            "data": target_dev,
        }


device_discovery = DeviceDiscovery()
