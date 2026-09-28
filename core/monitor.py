"""
Proactive Network & Node Monitoring Engine.
Runs background health-checks on configured routers/nodes and dispatches
automatic Telegram alerts on downtime, degradation, or recovery.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from config.settings import settings
from mikrotik.manager import device_manager

logger = logging.getLogger(__name__)


class ProactiveMonitor:
    def __init__(self):
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.is_running: bool = False
        self._loop_task: Optional[asyncio.Task] = None

    def _get_state(self, dev_id: str) -> Dict[str, Any]:
        if dev_id not in self.device_states:
            self.device_states[dev_id] = {
                "status": "UNKNOWN",
                "high_cpu": False,
                "high_cpu_count": 0,
                "normal_cpu_count": 0,
                "last_cpu_alert": 0.0,
                "fail_count": 0,
                "last_check": 0.0,
            }
        return self.device_states[dev_id]

    def check_devices(self) -> List[str]:
        """
        Poll all configured devices and return a list of alert messages for state changes.
        """
        alerts: List[str] = []
        now = time.time()

        for dev in settings.devices:
            # We don't spam alerts for mock demo unless configured
            if dev.protocol == "mock" and not settings.enable_mock_fallback:
                continue

            state = self._get_state(dev.id)
            client = device_manager.get_client(dev.name)
            conn_res = client.test_connection()
            is_online = conn_res.success

            prev_status = state["status"]

            if not is_online:
                state["fail_count"] += 1
                # If was ONLINE or UNKNOWN, trigger alert
                if prev_status == "ONLINE" and state["fail_count"] >= 1:
                    state["status"] = "OFFLINE"
                    alert_msg = (
                        f"🚨 **PERINGATAN DINI JARINGAN (ROUTER DOWN)**\n\n"
                        f"Perangkat **{dev.name}** (`{dev.host}`) terdeteksi **OFFLINE / Tidak Merespons**!\n"
                        f"• Protokol: `{dev.protocol.upper()}` (Port {dev.port})\n"
                        f"• Keterangan: {conn_res.message or 'Connection Timeout'}\n"
                        f"• Waktu Terdeteksi: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"⚠️ *Mohon segera periksa fisik perangkat atau jalur koneksi gateway.*"
                    )
                    alerts.append(alert_msg)
                    logger.warning("Proactive Alert: Device '%s' went OFFLINE.", dev.name)
                elif prev_status == "UNKNOWN":
                    state["status"] = "OFFLINE"

            else:
                # Device is reachable
                state["fail_count"] = 0
                if prev_status == "OFFLINE":
                    state["status"] = "ONLINE"
                    recovery_msg = (
                        f"✅ **JARINGAN PULIH (ROUTER RECOVERED)**\n\n"
                        f"Perangkat **{dev.name}** (`{dev.host}`) kini telah **ONLINE KEMBALI**!\n"
                        f"• Latency: `{conn_res.latency_ms} ms`\n"
                        f"• Waktu Pemulihan: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"🟢 *Layanan operasional jaringan telah normal kembali.*"
                    )
                    alerts.append(recovery_msg)
                    logger.info("Proactive Alert: Device '%s' RECOVERED.", dev.name)
                else:
                    state["status"] = "ONLINE"

                # Check CPU Threshold
                res = client.get_resource()
                if res.success and res.data:
                    if isinstance(res.data, dict):
                        cpu_load = int(res.data.get("cpu_load", 0))
                        uptime_val = res.data.get("uptime", "N/A")
                    else:
                        cpu_load = int(getattr(res.data, "cpu_load", 0))
                        uptime_val = getattr(res.data, "uptime", "N/A")

                    # Hysteresis margin: recovery occurs 15% below threshold (e.g. <= 75% for 90% threshold)
                    recovery_threshold = max(20.0, settings.cpu_threshold_percent - 15.0)
                    last_alert_time = state.get("last_cpu_alert", 0.0)
                    cooldown_passed = (now - last_alert_time) >= 900.0  # 15 minutes cooldown

                    if cpu_load >= settings.cpu_threshold_percent:
                        state["normal_cpu_count"] = 0
                        state["high_cpu_count"] = state.get("high_cpu_count", 0) + 1

                        if not state.get("high_cpu"):
                            # First occurrence of high CPU
                            state["high_cpu"] = True
                            state["last_cpu_alert"] = now
                            cpu_alert = (
                                f"⚠️ **PERINGATAN: BEBAN CPU TINGGI**\n\n"
                                f"Perangkat: **{dev.name}** (`{dev.host}`)\n"
                                f"• Penggunaan CPU: **{cpu_load}%** (Melebihi ambang batas {settings.cpu_threshold_percent:.0f}%)\n"
                                f"• Uptime: `{uptime_val}`\n"
                                f"• Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                f"💡 *Ketik 'Profile CPU' atau 'Cek traffic jaringan' ke bot untuk menganalisis beban.*"
                            )
                            alerts.append(cpu_alert)
                            logger.warning("Proactive Alert: High CPU (%d%%) on '%s'.", cpu_load, dev.name)
                        elif cooldown_passed:
                            # Periodic reminder if high CPU is persistent for >15 minutes
                            state["last_cpu_alert"] = now
                            cpu_reminder = (
                                f"⚠️ **PERINGATAN: BEBAN CPU MASIH TINGGI (PERSISTEN)**\n\n"
                                f"Perangkat: **{dev.name}** (`{dev.host}`)\n"
                                f"• Penggunaan CPU: **{cpu_load}%** (Masih di atas {settings.cpu_threshold_percent:.0f}% selama > 15 menit)\n"
                                f"• Uptime: `{uptime_val}`\n"
                                f"• Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                f"💡 *Ketik 'Profile CPU' untuk melihat proses sistem yang membebani router.*"
                            )
                            alerts.append(cpu_reminder)
                            logger.warning("Proactive Alert: Persistent High CPU (%d%%) on '%s'.", cpu_load, dev.name)

                    elif cpu_load <= recovery_threshold:
                        state["high_cpu_count"] = 0
                        if state.get("high_cpu"):
                            # CPU normalized safely below hysteresis threshold
                            state["high_cpu"] = False
                            state["normal_cpu_count"] = 0
                            recovery_alert = (
                                f"✅ **BEBAN CPU KEMBALI NORMAL**\n\n"
                                f"Perangkat: **{dev.name}** (`{dev.host}`)\n"
                                f"• Penggunaan CPU: **{cpu_load}%** (Stabil di bawah batas aman {recovery_threshold:.0f}%)\n"
                                f"• Uptime: `{uptime_val}`\n"
                                f"• Waktu Pemulihan: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                f"🟢 *Beban komputasi router telah stabil dan aman kembali.*"
                            )
                            alerts.append(recovery_alert)
                            logger.info("Proactive Alert: Device '%s' CPU normalized to %d%%.", dev.name, cpu_load)
                    else:
                        # Deadband / Hysteresis zone: maintain current state without flapping
                        state["normal_cpu_count"] = 0

            state["last_check"] = now

        return alerts

    async def run_monitoring_loop(self, bot: Any) -> None:
        """
        Continuous background monitoring loop.
        Dispatches alert messages to configured alert_chat_ids.
        """
        if not settings.monitoring_enabled:
            logger.info("Proactive monitoring is disabled in settings.")
            return

        self.is_running = True
        logger.info(
            "Memulai Proactive Network Monitor (Interval: %ds, Target Chats: %s)...",
            settings.monitoring_interval_seconds,
            settings.alert_chat_ids,
        )

        # Initial delay before starting the first check
        await asyncio.sleep(5)

        while self.is_running:
            try:
                loop = asyncio.get_running_loop()
                # Run sync device polling in default thread executor to avoid blocking the event loop
                alerts = await loop.run_in_executor(None, self.check_devices)

                if alerts and settings.alert_chat_ids:
                    for alert_text in alerts:
                        for chat_id in settings.alert_chat_ids:
                            try:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=alert_text,
                                    parse_mode="Markdown",
                                )
                            except Exception as send_err:
                                logger.error("Gagal mengirim alert ke chat_id %s: %s", chat_id, send_err)

            except Exception as e:
                logger.error("Error dalam proactive monitoring loop: %s", e, exc_info=True)

            await asyncio.sleep(settings.monitoring_interval_seconds)

    def stop(self) -> None:
        self.is_running = False


proactive_monitor = ProactiveMonitor()
