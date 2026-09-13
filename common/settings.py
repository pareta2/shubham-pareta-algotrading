"""
common/settings.py
------------------
Reads config/settings.json and gives it to the rest of the program.

Why a JSON file?  Because it is the simplest thing a beginner can open in
Notepad / TextEdit and edit without touching any Python code.
"""

import json
from pathlib import Path

# ROOT = the folder that contains main.py (one level above this file's folder)
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
EXAMPLE_FILE = CONFIG_DIR / "settings.example.json"


def load_settings() -> dict:
    """Return the whole settings.json as a Python dictionary."""
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(
            "\n\n  config/settings.json not found!\n"
            "  Fix: copy config/settings.example.json  ->  config/settings.json\n"
            "       and fill in your Zerodha + Gmail details.\n"
        )
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get(settings: dict, *keys, default=None):
    """
    Safe nested lookup.   get(settings, "zerodha", "user_id")
    Returns `default` instead of crashing when a key is missing.
    """
    value = settings
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value
