"""
auth  (package entry point)
---------------------------
The ONE function every other module should call:

    from auth import get_kite
    kite = get_kite()          # -> a ready-to-use KiteClient

What get_kite() does:
    1. If config/session.json exists and still works -> use it (no login).
    2. Otherwise log in with the mode from settings.json and save the new session.

Login modes (settings.json -> auth.mode):
    "api_key"  official Kite Connect API key   <- RECOMMENDED, shown on the channel
    "auto"     enctoken via Gmail-OTP / TOTP    <- unofficial, see README disclaimer
    "manual"   enctoken via local browser page  <- unofficial, see README disclaimer

You can force a fresh login with  get_kite(force_new=True)
or choose the mode explicitly     get_kite(mode="manual").
"""

from typing import Optional

from auth.token_store import clear_session, load_session, save_session
from broker.kite_client import KiteClient
from common.logger import log
from common.settings import get, load_settings

MODES = ("api_key", "auto", "manual")


def authenticate(mode: Optional[str] = None) -> dict:
    """Run a full login and return the session dict (also saved to disk)."""
    settings = load_settings()
    mode = (mode or get(settings, "auth", "mode", default="api_key")).lower()
    user_id = get(settings, "zerodha", "user_id", default="")

    if mode == "api_key":
        from auth.api_key_auth import api_key_login
        session = api_key_login(settings)
    elif mode == "auto":
        from auth.auto_auth import auto_login
        session = {"auth_type": "enctoken", "enctoken": auto_login(settings), "user_id": user_id}
    elif mode == "manual":
        from auth.manual_auth import manual_login
        session = {"auth_type": "enctoken", "enctoken": manual_login(settings), "user_id": user_id}
    else:
        raise ValueError(f"Unknown auth mode '{mode}'. Use one of: {', '.join(MODES)}")

    save_session(session)
    log("Session saved to config/session.json", "ok")
    return session


def get_kite(mode: Optional[str] = None, force_new: bool = False) -> KiteClient:
    """Return a working KiteClient, logging in only when needed."""
    if not force_new:
        saved = load_session()
        if saved:
            kite = KiteClient.from_session(saved)
            if kite.is_token_valid():
                log(f"Using saved {saved.get('auth_type')} session from {saved.get('generated_at')}", "ok")
                return kite
            log("Saved session has expired - logging in again", "warn")
            clear_session()

    return KiteClient.from_session(authenticate(mode))
