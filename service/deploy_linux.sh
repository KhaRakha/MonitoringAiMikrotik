#!/usr/bin/env bash
# ==============================================================================
# 1-Click Deployment Script for MikroTik AI Agent on Linux (VPS / Raspberry Pi / STB)
# ==============================================================================
set -e

echo "================================================================"
echo " MikroTik AI Agent - Linux 24/7 Deployment Installer"
echo "================================================================"

# Check root
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Harap jalankan script ini sebagai root (sudo bash deploy_linux.sh)"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[1/5] Memperbarui paket sistem dan menginstall dependensi..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl iputils-ping

echo "[2/5] Menyiapkan Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "[3/5] Menginstall dependensi requirements.txt..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "[4/5] Memasang Systemd Service (mikrotik-ai.service)..."
SERVICE_FILE="/etc/systemd/system/mikrotik-ai.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=MikroTik AI Agent Telegram Bot
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/service/watchdog.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Jakarta

[Install]
WantedBy=multi-user.target
EOF

echo "[5/5] Mengaktifkan dan menjalankan service..."
systemctl daemon-reload
systemctl enable mikrotik-ai.service
systemctl restart mikrotik-ai.service

echo ""
echo "================================================================"
echo " [SUKSES] MikroTik AI Agent Berhasil Dideploy 24/7 di Server!"
echo " Status Service: systemctl status mikrotik-ai"
echo " Lihat Log Realtime: journalctl -u mikrotik-ai -f"
echo " Restart Bot: systemctl restart mikrotik-ai"
echo " Stop Bot: systemctl stop mikrotik-ai"
echo "================================================================"
