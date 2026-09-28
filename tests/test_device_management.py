"""
Unit tests for dynamic device registration and removal via bot / tools.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import yaml
from config.settings import CONFIG_DIR, DeviceConfig, settings
from core.agent import hermes_agent
from core.confirmation import confirmation_manager
from mikrotik.discovery import device_discovery
from mikrotik.tools import register_device, remove_device


def test_register_and_remove_device_lifecycle():
    test_dev_name = "Unit_Test_Router"
    test_ip = "192.168.99.254"

    # Clean up before
    device_discovery.remove_device(test_dev_name)

    # 1. Register device
    res = register_device(
        name=test_dev_name,
        host=test_ip,
        protocol="api",
        port=8728,
        username="admin",
        password="secretpassword",
        description="Testing Dynamic Device Add",
    )

    assert res["success"] is True
    assert "berhasil didaftarkan" in res["message"].lower()

    # Verify device exists in settings
    found = settings.find_device(test_dev_name, fallback=False)
    assert found is not None
    assert found.host == test_ip
    assert found.port == 8728

    # Duplicate check
    dup = register_device(name=test_dev_name, host=test_ip)
    assert dup["success"] is False

    # 2. Remove device
    del_res = remove_device(test_dev_name)
    assert del_res["success"] is True
    assert "berhasil dihapus" in del_res["message"].lower()

    # Verify removed from settings
    found_after = settings.find_device(test_dev_name, fallback=False)
    assert found_after is None


def test_natural_language_add_device_requires_confirmation():
    # Admin user sends request to add router via natural language
    user_id = 999999
    # Add to admin ids temporarily if not present
    if user_id not in settings.admin_telegram_ids:
        settings.admin_telegram_ids.append(user_id)
        settings.allowed_telegram_ids.append(user_id)

    # Clean up before
    remove_device("192.168.55.1")

    prompt = "Daftarkan router baru Lab Multimedia IP 192.168.55.1 port 8728 username admin password rahasia123"
    result = hermes_agent.process_message(user_id=user_id, username="TestAdmin", text=prompt)

    assert result["pending_action"] is not None
    assert result["pending_action"].action_name == "register_device"
    assert result["pending_action"].arguments["host"] == "192.168.55.1"
    assert "Konfirmasi Pendaftaran Router Baru" in result["reply"]

    # Confirm action
    token = result["pending_action"].token
    exec_res = confirmation_manager.execute_action(token)
    assert exec_res.success is True

    # Verify it was added
    found = settings.find_device("192.168.55.1", fallback=False)
    assert found is not None

    # Clean up after
    remove_device("192.168.55.1")
