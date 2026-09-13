"""
common/logger.py
----------------
One tiny helper so every module prints messages in the same style:

    [12:30:05] ✅ Login successful

Use:   from common.logger import log
       log("hello")            # normal message
       log("oops", level="error")
"""

from datetime import datetime

ICONS = {
    "info": "ℹ️ ",
    "ok": "✅",
    "warn": "⚠️ ",
    "error": "❌",
    "step": "➡️ ",
}


def log(message: str, level: str = "info") -> None:
    now = datetime.now().strftime("%H:%M:%S")
    icon = ICONS.get(level, "")
    print(f"[{now}] {icon} {message}")
