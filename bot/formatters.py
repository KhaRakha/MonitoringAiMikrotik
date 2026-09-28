"""
Formatting utilities for Telegram messages, cards, buttons, and reports.
"""

from __future__ import annotations

from typing import Any, Dict, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def make_confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    """Create Telegram inline keyboard for confirmation."""
    keyboard = [
        [
            InlineKeyboardButton("✅ YA (Setuju)", callback_data=f"conf_yes:{token}"),
            InlineKeyboardButton("❌ BATAL (Tolak)", callback_data=f"conf_no:{token}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def format_device_list(devices: List[Dict[str, Any]]) -> str:
    """Format configured devices list into an attractive Telegram card."""
    lines = ["📋 **Daftar Perangkat MikroTik Terdaftar**\n"]
    for dev in devices:
        icon = "🟢" if dev.get("online") else "🔴"
        default_tag = " `[Default]`" if dev.get("is_default") else ""
        lines.append(
            f"{icon} **{dev.get('name')}**{default_tag}\n"
            f"   • Host/IP : `{dev.get('host')}:{dev.get('port')}`\n"
            f"   • Protokol: `{dev.get('protocol').upper()}`\n"
            f"   • Status  : {dev.get('status_message', 'OK')}\n"
        )
    lines.append("💡 *Gunakan nama perangkat dalam pertanyaan Anda (misal: 'cek resource kantor cabang').*")
    return "\n".join(lines)


def format_audit_logs(logs: List[Dict[str, Any]]) -> str:
    """Format audit trail logs for Telegram view."""
    if not logs:
        return "📜 Belum ada catatan aktivitas audit."

    lines = ["📜 **Catatan Audit Trail Aktivitas Terakhir**\n"]
    for log in logs:
        res_icon = "✅" if log.get("result_status") == "SUCCESS" else ("⚠️" if log.get("result_status") == "BLOCKED" else "❌")
        lines.append(
            f"{res_icon} `[{log.get('timestamp')}]`\n"
            f"• User   : `{log.get('telegram_user_name')}` (`{log.get('telegram_user_id')}`)\n"
            f"• Target : **{log.get('target_device')}**\n"
            f"• Aksi   : `{log.get('action_name')}` ({log.get('action_category')})\n"
            f"• Status : **{log.get('result_status')}** (Konfirmasi: `{log.get('confirmation_status')}`)\n"
            f"• Prompt : *\"{log.get('user_prompt')}\"*\n"
        )
    return "\n".join(lines)
