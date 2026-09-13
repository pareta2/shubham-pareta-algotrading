"""
auth/token_store.py
-------------------
Saves the enctoken to  config/enctoken.json  so you don't have to log in
again every time you run a script.  A Zerodha enctoken normally works until
the next morning (~ 7-8 AM), when Zerodha expires all sessions.
"""

import json
from datetime import datetime
from typing import Optional

from common.settings import CONFIG_DIR

TOKEN_FILE = CONFIG_DIR / "enctoken.json"


def save_token(enctoken: str, user_id: str) -> None:
    data = {
        "user_id": user_id,
        "enctoken": enctoken,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_token() -> Optional[dict]:
    """Returns {'user_id', 'enctoken', 'generated_at'} or None if no file."""
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_token() -> None:
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
