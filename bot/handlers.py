"""
Telegram Bot Handlers.
Dispatches bot commands, callback queries, and natural language messages to Hermes AI Agent.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from bot.formatters import format_audit_logs, format_device_list, make_confirmation_keyboard
from config.settings import settings
from core.agent import conversation_memory, hermes_agent
from core.audit import audit_logger
from core.confirmation import confirmation_manager
from core.security import security_manager
from mikrotik.discovery import device_discovery
from mikrotik.manager import device_manager

logger = logging.getLogger(__name__)


async def _safe_reply_text(message: Any, text: str, reply_markup: Any = None) -> Any:
    """Send reply with Markdown parsing, chunking if message exceeds Telegram limit (4096 chars)."""
    # Guard against Telegram 4096 character limit
    if len(text) > 4000:
        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        last_resp = None
        for idx, chunk in enumerate(chunks):
            # Only attach markup to the final chunk
            markup = reply_markup if idx == len(chunks) - 1 else None
            try:
                last_resp = await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
            except Exception:
                last_resp = await message.reply_text(chunk, reply_markup=markup)
        return last_resp

    try:
        return await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except Exception:
        return await message.reply_text(text, reply_markup=reply_markup)


async def _safe_edit_message_text(target: Any, text: str, reply_markup: Any = None) -> Any:
    """Edit message with Markdown parsing, fallback to plain text if malformed."""
    display_text = text[:4000] if len(text) > 4000 else text
    try:
        return await target.edit_message_text(display_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except Exception:
        return await target.edit_message_text(display_text, reply_markup=reply_markup)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command."""
    user = update.effective_user
    if not user:
        return

    if not security_manager.is_user_authorized(user.id):
        await update.message.reply_text(
            f"⛔ **Akses Ditolak**\n\n"
            f"User ID Anda `{user.id}` belum terdaftar dalam daftar izin (whitelist).\n"
            f"Hubungi Administrator sistem untuk menambahkan ID Anda.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    role = security_manager.get_user_role(user.id)
    role_badge = "🛡️ **Administrator**" if role == "ADMIN" else "👁️ **Viewer (Read-Only)**"

    welcome_text = (
        f"👋 Halo, **{user.first_name}**!\n"
        f"Role Akses Anda: {role_badge}\n\n"
        f"Saya adalah **Hermes AI Agent** untuk otomatisasi dan pengelolaan MikroTik RouterOS.\n\n"
        f"🤖 **Fitur Utama:**\n"
        f"• **Natural Language**: Cukup gunakan bahasa sehari-hari tanpa perlu menghafal command RouterOS.\n"
        f"• **Multi-Perangkat**: Mendukung banyak router (Kantor Utama, Cabang, Lab).\n"
        f"• **Proactive Alerting**: Memantau router dan mengirim notifikasi otomatis jika down.\n"
        f"• **Sistem Konfirmasi Aman**: Perubahan konfigurasi wajib disetujui terlebih dahulu.\n"
        f"• **Perlindungan Berbahaya**: Menolak operasi destruktif (reset/reboot).\n\n"
        f"💡 **Contoh Pertanyaan:**\n"
        f"• *'Coba cek kondisi MikroTik kantor utama'* (Monitoring)\n"
        f"• *'Kenapa internet kantor terasa lambat?'* (Troubleshooting)\n"
        f"• *'Cek user hotspot yang sedang aktif'* (Status Hotspot)\n"
        f"• *'Cek port 80 pada web server 10.20.33.10'* (Server Check)\n"
        f"• *'Buatkan user hotspot untuk tamu bernama Tamu123, aktif satu hari'* (Konfigurasi)\n\n"
        f"Ketik `/help` untuk bantuan lengkap atau langsung kirimkan pertanyaan Anda!"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


async def role_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /role command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    role = security_manager.get_user_role(user.id)
    can_write = security_manager.can_user_write(user.id)
    text = (
        f"👤 **Profil & Hak Akses Pengguna**\n\n"
        f"• Nama: **{user.first_name}**\n"
        f"• Telegram User ID: `{user.id}`\n"
        f"• Role Sistem: **{role}**\n"
        f"• Izin Konfigurasi (Write): {'✅ Diizinkan' if can_write else '❌ Terbatas (Read-Only)'}\n\n"
        f"💡 *Role dapat dikonfigurasi melalui ADMIN_TELEGRAM_IDS dan VIEWER_TELEGRAM_IDS pada file .env.*"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    role = security_manager.get_user_role(user.id)
    help_text = (
        f"📖 **Panduan Penggunaan Hermes AI Agent MikroTik**\n"
        f"Role Anda: **{role}**\n\n"
        f"**Perintah Cepat:**\n"
        f"• `/status` - Cek ringkas kondisi router aktif\n"
        f"• `/devices` - Tampilkan daftar semua router MikroTik\n"
        f"• `/add_device` - Daftarkan router baru langsung dari Telegram\n"
        f"• `/remove_device` - Hapus router dari daftar pemantauan\n"
        f"• `/add_ip` - Tambahkan IP address baru pada interface MikroTik\n"
        f"• `/remove_ip` - Hapus IP address dari router MikroTik\n"
        f"• `/edit_ip` - Ubah (edit) IP address atau interface router\n"
        f"• `/discover` - Pindai subnet untuk menemukan router baru\n"
        f"• `/audit` - Tampilkan log riwayat aktivitas administrasi\n"
        f"• `/role` - Cek status profil dan hak akses Anda\n"
        f"• `/clear` - Bersihkan riwayat sesi obrolan (reset context memori)\n\n"
        f"**Bahasa Natural (AI):**\n"
        f"Anda tidak perlu mengetik command garis miring! Anda bebas bertanya:\n"
        f"1. *\"Tambahkan IP 192.168.50.1/24 di interface ether2\"*\n"
        f"2. *\"Ubah IP 192.168.10.1 menjadi 192.168.20.1/24\"*\n"
        f"3. *\"Hapus IP 192.168.50.1\"*\n"
        f"4. *\"Daftarkan router baru Cabang B IP 192.168.20.1 port 8728 username admin password rahasia\"*\n"
        f"5. *\"Cek kondisi Kantor Cabang\"*\n"
        f"6. *\"Tolong lihat perangkat apa saja yang terhubung ke jaringan.\"*\n"
        f"7. *\"Tambahkan netwatch untuk host 192.168.50.1\"*\n\n"
        f"🔒 **Keamanan:**\n"
        f"Setiap operasi yang mengubah konfigurasi router akan memunculkan tombol konfirmasi `[ YA ]` dan `[ BATAL ]` (khusus Administrator)."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /devices command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    dev_list = device_manager.list_devices()
    text = format_device_list(dev_list)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def add_device_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /add_device command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    if not security_manager.can_user_write(user.id):
        await update.message.reply_text(
            "⛔ **Akses Terbatas**: Akun Anda memiliki role **Viewer (Read-Only)**. Pendaftaran perangkat hanya dapat dilakukan oleh Administrator.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    args = context.args or []
    if not args:
        guide = (
            "📋 **Panduan Pendaftaran Router Baru (/add_device)**\n\n"
            "Format perintah:\n"
            "`/add_device <Nama> <IP> [Port] [Protokol] [Username] [Password]`\n\n"
            "💡 **Contoh Cepat:**\n"
            "`/add_device Cabang_2 192.168.88.1 8728 api admin rahasia123`\n"
            "`/add_device Lab_PTI 192.168.10.1 80 rest admin pass456`\n\n"
            "Keterangan:\n"
            "• **Nama**: Nama router (gunakan `_` jika lebih dari 1 kata)\n"
            "• **IP**: Alamat IP host router / IP VPN\n"
            "• **Port**: `8728` (RouterOS API), `80` (REST), atau `22` (SSH)\n"
            "• **Protokol**: `api` (rekomendasi), `rest`, atau `ssh`\n"
            "• **Username**: default `admin`\n"
            "• **Password**: password login router\n\n"
            "💡 *Anda juga bisa langsung chat bahasa biasa, contoh:*\n"
            "*\"Daftarkan router baru Cabang B dengan IP 192.168.20.1 port 8728 username admin password rahasia\"*"
        )
        await update.message.reply_text(guide, parse_mode=ParseMode.MARKDOWN)
        return

    name = args[0]
    host = args[1] if len(args) > 1 else ""
    if not host:
        await update.message.reply_text(
            "⚠️ Mohon cantumkan alamat IP router target.\nContoh: `/add_device Cabang_2 192.168.88.1`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    port = 0
    proto = "api"
    username = "admin"
    password = ""

    if len(args) > 2 and args[2].isdigit():
        port = int(args[2])
    if len(args) > 3 and args[3].lower() in ("api", "rest", "ssh", "mock"):
        proto = args[3].lower()
    if len(args) > 4:
        username = args[4]
    if len(args) > 5:
        password = args[5]

    loading_msg = await update.message.reply_text(
        f"⏳ Mendaftarkan dan menguji router **{name}** (`{host}`)...",
        parse_mode=ParseMode.MARKDOWN,
    )

    res = await asyncio.to_thread(
        device_discovery.register_device,
        name=name,
        host=host,
        protocol=proto,
        port=port,
        username=username,
        password=password,
        description=f"Router MikroTik {name} (Didaftarkan via Telegram)",
    )

    if not res.get("success"):
        await loading_msg.edit_text(
            f"❌ **Gagal Mendaftarkan Router**\n\n{res.get('message')}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Test connection immediately
    client = device_manager.get_client(name)
    test_res = await asyncio.to_thread(client.test_connection)
    status_icon = "🟢 **Online**" if test_res.success else "🔴 **Offline / Belum Terjangkau**"
    latency_info = f"• Latency: `{test_res.latency_ms} ms`\n" if test_res.success else f"• Keterangan: `{test_res.message}`\n"

    audit_logger.log_event(
        telegram_user_id=user.id,
        telegram_user_name=user.username or user.first_name,
        user_prompt=f"/add_device {' '.join(args)}",
        target_device=name,
        action_category="INVENTORY",
        action_name="register_device",
        confirmation_status="APPROVED",
        result_status="SUCCESS",
        details=res.get("data", {}),
    )

    success_text = (
        f"✅ **Router Berhasil Didaftarkan ke Sistem!**\n\n"
        f"• Nama: **{name}**\n"
        f"• Host/IP: `{host}` (Port `{res['data']['port']}`)\n"
        f"• Protokol: `{proto.upper()}`\n"
        f"• Status Koneksi: {status_icon}\n"
        f"{latency_info}\n"
        f"🔄 Perangkat ini sekarang otomatis dipantau oleh background monitor.\n"
        f"💡 Anda bisa langsung mengontrolnya, contoh:\n"
        f"👉 *\"Cek kondisi {name}\"*\n"
        f"👉 `/devices`"
    )
    await loading_msg.edit_text(success_text, parse_mode=ParseMode.MARKDOWN)


async def remove_device_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /remove_device command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    if not security_manager.can_user_write(user.id):
        await update.message.reply_text(
            "⛔ **Akses Terbatas**: Akun Anda memiliki role **Viewer (Read-Only)**. Penghapusan perangkat hanya dapat dilakukan oleh Administrator.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "⚠️ **Format Perintah /remove_device**\n\n"
            "Ketik: `/remove_device <Nama_atau_ID>`\n"
            "Contoh: `/remove_device Cabang_2`\n\n"
            "Gunakan `/devices` untuk melihat daftar nama perangkat yang terdaftar.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target = " ".join(args).strip()
    res = await asyncio.to_thread(device_discovery.remove_device, name_or_id=target)
    if res.get("success"):
        audit_logger.log_event(
            telegram_user_id=user.id,
            telegram_user_name=user.username or user.first_name,
            user_prompt=f"/remove_device {target}",
            target_device=target,
            action_category="INVENTORY",
            action_name="remove_device",
            confirmation_status="APPROVED",
            result_status="SUCCESS",
            details=res.get("data", {}),
        )
        await update.message.reply_text(f"🗑️ {res.get('message')}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ {res.get('message')}", parse_mode=ParseMode.MARKDOWN)


async def add_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /add_ip command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    if not security_manager.can_user_write(user.id):
        await update.message.reply_text(
            "⛔ **Akses Terbatas**: Akun Anda memiliki role **Viewer (Read-Only)**. Penambahan IP address hanya dapat dilakukan oleh Administrator.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    args = context.args or []
    if len(args) < 2:
        guide = (
            "📋 **Panduan Penambahan IP Address (/add_ip)**\n\n"
            "Format perintah:\n"
            "`/add_ip <IP/CIDR> <Interface> [Komentar] [Router]`\n\n"
            "💡 **Contoh Cepat:**\n"
            "`/add_ip 192.168.50.1/24 ether2`\n"
            "`/add_ip 10.10.10.1/24 ether3 \"LAN Guru\" Kantor_Cabang`\n\n"
            "Keterangan:\n"
            "• **IP/CIDR**: Alamat IP dan prefix subnet (contoh: `192.168.50.1/24`)\n"
            "• **Interface**: Nama port interface MikroTik (contoh: `ether2`, `wlan1`)\n"
            "• **Komentar**: Catatan opsional\n"
            "• **Router**: Nama router target jika ada lebih dari 1 router\n\n"
            "💡 *Bisa juga via chat natural:*\n"
            "*\"Tambahkan IP 192.168.50.1/24 di interface ether2\"*"
        )
        await update.message.reply_text(guide, parse_mode=ParseMode.MARKDOWN)
        return

    address = args[0]
    if "/" not in address:
        address = f"{address}/24"
    interface = args[1]
    comment = args[2] if len(args) > 2 else ""
    device_arg = args[3] if len(args) > 3 else ""
    dev = settings.find_device(device_arg)
    dev_name = dev.name if dev else settings.default_device_name

    arguments = {
        "device": dev_name,
        "address": address,
        "interface": interface,
        "comment": comment,
    }

    pending = confirmation_manager.create_pending_action(
        user_id=user.id,
        device_name=dev_name,
        action_name="add_ip_address",
        arguments=arguments,
        description=f"Penambahan IP '{address}' pada interface '{interface}' ({dev_name})",
    )

    confirm_card = (
        f"⚠️ **Konfirmasi Penambahan IP Address**\n\n"
        f"• Target Router : **{dev_name}**\n"
        f"• Alamat IP     : `{address}`\n"
        f"• Interface     : `{interface}`\n"
        f"• Komentar      : `{comment or '-'}`\n\n"
        f"Tambahkan IP ini ke router?\n"
        f"👉 Balas **Ya** atau tekan tombol [ YA ] di bawah."
    )
    keyboard = make_confirmation_keyboard(pending.token)
    await _safe_reply_text(update.message, confirm_card, reply_markup=keyboard)


async def remove_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /remove_ip command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    if not security_manager.can_user_write(user.id):
        await update.message.reply_text(
            "⛔ **Akses Terbatas**: Akun Anda memiliki role **Viewer (Read-Only)**. Penghapusan IP address hanya dapat dilakukan oleh Administrator.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    args = context.args or []
    if not args:
        guide = (
            "📋 **Panduan Penghapusan IP Address (/remove_ip)**\n\n"
            "Format perintah:\n"
            "`/remove_ip <IP_Address> [Router]`\n\n"
            "💡 **Contoh:**\n"
            "`/remove_ip 192.168.50.1`\n"
            "`/remove_ip 192.168.50.1/24 Kantor_Cabang`\n\n"
            "💡 *Bisa juga via chat natural:*\n"
            "*\"Hapus IP 192.168.50.1\"*"
        )
        await update.message.reply_text(guide, parse_mode=ParseMode.MARKDOWN)
        return

    address = args[0]
    device_arg = args[1] if len(args) > 1 else ""
    dev = settings.find_device(device_arg)
    dev_name = dev.name if dev else settings.default_device_name

    arguments = {
        "device": dev_name,
        "address": address,
    }

    pending = confirmation_manager.create_pending_action(
        user_id=user.id,
        device_name=dev_name,
        action_name="remove_ip_address",
        arguments=arguments,
        description=f"Penghapusan IP address '{address}' ({dev_name})",
    )

    confirm_card = (
        f"⚠️ **Konfirmasi Penghapusan IP Address**\n\n"
        f"• Target Router : **{dev_name}**\n"
        f"• Alamat IP     : `{address}`\n\n"
        f"Hapus konfigurasi IP address ini dari router?\n"
        f"👉 Balas **Ya** atau tekan tombol [ YA ] di bawah."
    )
    keyboard = make_confirmation_keyboard(pending.token)
    await _safe_reply_text(update.message, confirm_card, reply_markup=keyboard)


async def edit_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /edit_ip command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    if not security_manager.can_user_write(user.id):
        await update.message.reply_text(
            "⛔ **Akses Terbatas**: Akun Anda memiliki role **Viewer (Read-Only)**. Pengubahan IP address hanya dapat dilakukan oleh Administrator.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    args = context.args or []
    if len(args) < 2:
        guide = (
            "📋 **Panduan Ubah / Edit IP Address (/edit_ip)**\n\n"
            "Format perintah:\n"
            "`/edit_ip <IP_Lama> <IP_Baru> [Interface_Baru] [Router]`\n\n"
            "💡 **Contoh:**\n"
            "`/edit_ip 192.168.10.1 192.168.20.1/24`\n"
            "`/edit_ip 192.168.10.1 192.168.20.1/24 ether3 Kantor_Cabang`\n\n"
            "💡 *Bisa juga via chat natural:*\n"
            "*\"Ubah IP 192.168.10.1 menjadi 192.168.20.1/24\"*"
        )
        await update.message.reply_text(guide, parse_mode=ParseMode.MARKDOWN)
        return

    curr_ip = args[0]
    new_ip = args[1]
    if "/" not in new_ip:
        new_ip = f"{new_ip}/24"
    new_iface = args[2] if len(args) > 2 else ""
    device_arg = args[3] if len(args) > 3 else ""
    dev = settings.find_device(device_arg)
    dev_name = dev.name if dev else settings.default_device_name

    arguments = {
        "device": dev_name,
        "current_address": curr_ip,
        "new_address": new_ip,
        "new_interface": new_iface,
    }

    pending = confirmation_manager.create_pending_action(
        user_id=user.id,
        device_name=dev_name,
        action_name="set_ip_address",
        arguments=arguments,
        description=f"Pengubahan IP address '{curr_ip}' -> '{new_ip}' ({dev_name})",
    )

    confirm_card = (
        f"⚠️ **Konfirmasi Pengubahan IP Address**\n\n"
        f"• Target Router : **{dev_name}**\n"
        f"• IP Lama       : `{curr_ip}`\n"
        f"• IP Baru       : `{new_ip}`\n"
        f"• Interface     : `{new_iface or '(Tetap)'}`\n\n"
        f"Lanjutkan perubahan IP address ini?\n"
        f"👉 Balas **Ya** atau tekan tombol [ YA ] di bawah."
    )
    keyboard = make_confirmation_keyboard(pending.token)
    await _safe_reply_text(update.message, confirm_card, reply_markup=keyboard)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /status command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    # Trigger monitoring scenario on default device
    result = await asyncio.to_thread(
        hermes_agent.process_message,
        user_id=user.id,
        username=user.username or user.first_name,
        text="Cek kondisi router",
    )
    await _safe_reply_text(update.message, result["reply"])


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /clear command to reset user conversation memory buffer."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    conversation_memory.clear(user.id)
    await _safe_reply_text(
        update.message,
        "🧹 **Riwayat percakapan telah dibersihkan.**\nSesi dialog baru dimulai!"
    )


async def audit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /audit command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    logs = audit_logger.get_recent_logs(limit=8)
    text = format_audit_logs(logs)
    await _safe_reply_text(update.message, text)


async def discover_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /discover command."""
    user = update.effective_user
    if not user or not security_manager.is_user_authorized(user.id):
        return

    msg = await update.message.reply_text("🔍 Memindai jaringan lokal untuk menemukan router MikroTik...", parse_mode=ParseMode.MARKDOWN)

    # Scan default subnet non-blockingly
    discovered = await asyncio.to_thread(device_discovery.scan_subnet, subnet_cidr="10.20.33.0/24")
    if not discovered:
        # Also try default 192.168.88.0/24
        discovered = await asyncio.to_thread(device_discovery.scan_subnet, subnet_cidr="192.168.88.0/24")

    if not discovered:
        await msg.edit_text("🔍 Pemindaian selesai. Tidak ditemukan perangkat MikroTik baru pada subnet lokal.", parse_mode=ParseMode.MARKDOWN)
        return

    lines = [f"🔍 **Hasil Pemindaian Jaringan MikroTik:**\n"]
    for d in discovered:
        p_str = ", ".join(map(str, d.get("open_ports", [])))
        proto = d.get('suggested_protocol', 'api')
        port = 8728 if proto == 'api' else 80
        lines.append(f"• IP: `{d.get('ip')}` | Open Ports: `[{p_str}]` | Saran: `{proto.upper()}`")
        lines.append(f"  👉 Salin: `/add_device Router_Baru {d.get('ip')} {port} {proto} admin password`\n")

    lines.append("💡 *Klik atau salin perintah di atas untuk langsung mendaftarkan router tanpa membuka kode!*")
    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for natural language user messages."""
    user = update.effective_user
    if not user:
        return

    if not security_manager.is_user_authorized(user.id):
        await update.message.reply_text(
            f"⛔ **Akses Ditolak**\nUser ID `{user.id}` tidak diizinkan menggunakan bot ini.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    text = update.message.text
    if not text:
        return

    # Send typing action indicator
    await update.message.chat.send_action("typing")

    username = user.first_name or user.username or f"User_{user.id}"
    try:
        result = await asyncio.to_thread(hermes_agent.process_message, user_id=user.id, username=username, text=text)
        reply_text = result.get("reply", "Maaf, tidak ada respon.")
        pending_act = result.get("pending_action")

        if pending_act:
            keyboard = make_confirmation_keyboard(pending_act.token)
            await _safe_reply_text(update.message, reply_text, reply_markup=keyboard)
        else:
            await _safe_reply_text(update.message, reply_text)
    except Exception as e:
        logger.error("Error saat memproses pesan user: %s", e, exc_info=True)
        await _safe_reply_text(
            update.message,
            f"⚠️ Terjadi kendala saat memproses permintaan Anda: `{e}`\n"
            f"Silakan coba sesaat lagi atau gunakan perintah `/status`.",
        )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for inline button confirmation clicks."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data or ""

    if not security_manager.is_user_authorized(user.id):
        await query.edit_message_text("⛔ Anda tidak memiliki izin untuk tindakan ini.")
        return

    if data.startswith("conf_yes:"):
        token = data.split(":", 1)[1]
        action = confirmation_manager.get_action_by_token(token)
        if not action:
            await query.edit_message_text("⚠️ Aksi telah kedaluwarsa atau sudah dieksekusi sebelumnya.")
            return

        if not security_manager.can_user_write(user.id):
            await query.answer(
                "⛔ Akses Terbatas: Role Anda adalah Viewer (Read-Only). Hanya Admin yang dapat menyetujui perubahan.",
                show_alert=True,
            )
            return

        if action.user_id != user.id:
            await query.answer("Konfirmasi hanya dapat disetujui oleh pengguna yang mengajukan.", show_alert=True)
            return

        await _safe_edit_message_text(query, f"⏳ **Memproses eksekusi `{action.action_name}` pada {action.device_name}...**")
        res = await asyncio.to_thread(confirmation_manager.execute_action, token)

        audit_logger.log_event(
            telegram_user_id=user.id,
            telegram_user_name=user.username or user.first_name,
            user_prompt=f"Callback Approval for {action.action_name}",
            target_device=action.device_name,
            action_category="CONFIG",
            action_name=action.action_name,
            confirmation_status="APPROVED",
            result_status="SUCCESS" if res.success else "FAILED",
            details=res.to_dict(),
        )

        final_msg = f"{res.message}\n\nOperasi selesai."
        await _safe_edit_message_text(query, final_msg)

    elif data.startswith("conf_no:"):
        token = data.split(":", 1)[1]
        action = confirmation_manager.get_action_by_token(token)
        if action:
            confirmation_manager.cancel_action(token)
            audit_logger.log_event(
                telegram_user_id=user.id,
                telegram_user_name=user.username or user.first_name,
                user_prompt=f"Callback Cancel for {action.action_name}",
                target_device=action.device_name,
                action_category="CONFIG",
                action_name=action.action_name,
                confirmation_status="REJECTED",
                result_status="CANCELLED",
            )
        await _safe_edit_message_text(query, "❌ **Konfigurasi telah dibatalkan oleh pengguna.**")
