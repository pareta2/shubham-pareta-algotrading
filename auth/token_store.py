"""
auth/token_store.py
-------------------
Saves the login session to  config/session.json  so you don't have to log
in again every time you run a script.

The file looks like one of these:

    {"auth_type": "api_key",  "api_key": "...", "access_token": "...", "user_id": "AB1234", ...}
    {"auth_type": "enctoken", "enctoken": "...", "user_id": "AB1234", ...}

Both kinds of token stop working early next morning (Zerodha expires all
sessions daily), so you log in once per trading day.
"""

import json
from datetime import datetime
from typing import Optional

from common.settings import CONFIG_DIR

SESSION_FILE = CONFIG_DIR / "session.json"
OLD_ENCTOKEN_FILE = CONFIG_DIR / "enctoken.json"     # file name used by the first version


def save_session(session: dict) -> None:
    session = dict(session)
    session["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)


def load_session() -> Optional[dict]:
    """The saved dict, or None if you have never logged in."""
    if not SESSION_FILE.exists() and OLD_ENCTOKEN_FILE.exists():
        # one-time upgrade from the old enctoken.json format
        with open(OLD_ENCTOKEN_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
        old["auth_type"] = "enctoken"
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2)
        OLD_ENCTOKEN_FILE.unlink()
    if not SESSION_FILE.exists():
        return None
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
