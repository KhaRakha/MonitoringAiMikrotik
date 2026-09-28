"""
Service runner entrypoint for MikroTik AI Agent Telegram Bot.
Ensures correct sys.path configuration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bot.telegram_bot import run_bot

if __name__ == "__main__":
    run_bot()
