"""
MikroTik SSH Client for executing RouterOS CLI commands.
Uses paramiko or Windows native OpenSSH client.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any, Dict, List, Optional
from mikrotik.base import BaseMikrotikClient, OperationResult


class MikrotikSshClient(BaseMikrotikClient):
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "admin",
        password: str = "",
        timeout: float = 5.0,
        **kwargs,
    ):
        super().__init__(host, port, username, password, timeout=timeout)

    def _exec_command(self, cmd: str) -> str:
        # Construct SSH command line using Windows built-in ssh.exe
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={int(self.timeout)}",
            "-p", str(self.port),
            f"{self.username}@{self.host}",
            cmd,
        ]
        proc = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=self.timeout + 3)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
        return proc.stdout

    def test_connection(self) -> OperationResult:
        start = time.time()
        try:
            out = self._exec_command("/system identity print")
            latency = (time.time() - start) * 1000
            return OperationResult(
                success=True,
                message=f"Koneksi SSH ke MikroTik {self.host}:{self.port} berhasil.",
                data={"output": out.strip()},
                device=self.device_name,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return OperationResult(
                success=False,
                message=f"Gagal koneksi SSH ke {self.host}:{self.port}.",
                error=str(e),
                device=self.device_name,
                latency_ms=latency,
            )

    def get_resource(self) -> OperationResult:
        try:
            out = self._exec_command("/system resource print")
            data: Dict[str, Any] = {}
            for line in out.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().replace(" ", "_").lower()
                    v = v.strip()
                    data[k] = v
            return OperationResult(success=True, data=data, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_interfaces(self) -> OperationResult:
        try:
            out = self._exec_command("/interface print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_ip_addresses(self) -> OperationResult:
        try:
            out = self._exec_command("/ip address print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_ip_routes(self) -> OperationResult:
        try:
            out = self._exec_command("/ip route print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_arp_table(self) -> OperationResult:
        try:
            out = self._exec_command("/ip arp print without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_dhcp_leases(self) -> OperationResult:
        try:
            out = self._exec_command("/ip dhcp-server lease print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_hotspot_users(self) -> OperationResult:
        try:
            out = self._exec_command("/ip hotspot user print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_hotspot_active(self) -> OperationResult:
        try:
            out = self._exec_command("/ip hotspot active print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_hotspot_profiles(self) -> OperationResult:
        try:
            out = self._exec_command("/ip hotspot user profile print detail without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_firewall_rules(self) -> OperationResult:
        try:
            out = self._exec_command("/ip firewall filter print without-paging")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def get_system_logs(self, limit: int = 30) -> OperationResult:
        try:
            out = self._exec_command(f"/log print without-paging")
            lines = out.splitlines()[-limit:]
            return OperationResult(success=True, data=lines, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def ping(self, target: str, count: int = 4) -> OperationResult:
        try:
            out = self._exec_command(f"/ping address={target} count={count}")
            return OperationResult(success=True, data={"raw": out}, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def create_hotspot_user(self, name: str, password: str = "", profile: str = "default", limit_uptime: str = "") -> OperationResult:
        try:
            cmd = f'/ip hotspot user add name="{name}" profile="{profile or "default"}"'
            if password:
                cmd += f' password="{password}"'
            if limit_uptime:
                cmd += f' limit-uptime="{limit_uptime}"'
            out = self._exec_command(cmd)
            return OperationResult(success=True, message=f"✅ User hotspot '{name}' dibuat via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def delete_hotspot_user(self, name: str) -> OperationResult:
        try:
            cmd = f'/ip hotspot user remove [find name="{name}"]'
            out = self._exec_command(cmd)
            return OperationResult(success=True, message=f"✅ User hotspot '{name}' dihapus via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def set_interface_state(self, interface_name: str, enabled: bool) -> OperationResult:
        try:
            action = "enable" if enabled else "disable"
            cmd = f'/interface {action} [find name="{interface_name}"]'
            out = self._exec_command(cmd)
            state_str = "diaktifkan" if enabled else "dinonaktifkan"
            return OperationResult(success=True, message=f"✅ Interface '{interface_name}' berhasil {state_str} via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def add_ip_address(self, address: str, interface: str, comment: str = "") -> OperationResult:
        try:
            cmd = f'/ip address add address="{address.strip()}" interface="{interface.strip()}"'
            if comment:
                cmd += f' comment="{comment}"'
            out = self._exec_command(cmd)
            return OperationResult(success=True, message=f"✅ IP address '{address}' ditambahkan via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def remove_ip_address(self, address: str) -> OperationResult:
        try:
            cmd = f'/ip address remove [find address~"{address.strip()}"]'
            out = self._exec_command(cmd)
            return OperationResult(success=True, message=f"✅ IP address '{address}' dihapus via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def set_ip_address(
        self,
        current_address: str,
        new_address: Optional[str] = None,
        new_interface: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> OperationResult:
        try:
            params = []
            if new_address:
                params.append(f'address="{new_address.strip()}"')
            if new_interface:
                params.append(f'interface="{new_interface.strip()}"')
            if comment is not None:
                params.append(f'comment="{comment}"')
            cmd = f'/ip address set [find address~"{current_address.strip()}"] {" ".join(params)}'
            out = self._exec_command(cmd)
            return OperationResult(success=True, message=f"✅ IP address '{current_address}' diperbarui via SSH.", data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)

    def execute_raw_command(self, path: str, command: str, params: Optional[Dict[str, Any]] = None) -> OperationResult:
        try:
            full_cmd = f"/{path.strip('/')} {command.strip('/')}"
            out = self._exec_command(full_cmd)
            return OperationResult(success=True, data=out, device=self.device_name)
        except Exception as e:
            return OperationResult(success=False, error=str(e), device=self.device_name)
