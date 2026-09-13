"""
auth  (package entry point)
---------------------------
The ONE function every other module should call:

    from auth import get_kite
    kite = get_kite()          # -> a ready-to-use KiteClient

What get_kite() does:
    1. If config/enctoken.json exists and the token still works -> use it.
    2. Otherwise log in (AUTO or MANUAL, as per settings.json) and save the new token.

You can force a fresh login with  get_kite(force_new=True)
or choose the mode explicitly     get_kite(mode="manual").
"""

from typing import Optional

from auth.token_store import clear_token, load_token, save_token
from broker.kite_client import KiteClient
from common.logger import log
from common.settings import get, load_settings


def authenticate(mode: Optional[str] = None) -> str:
    """Run a full login and return a fresh enctoken (also saved to disk)."""
    settings = load_settings()
    mode = (mode or get(settings, "auth", "mode", default="auto")).lower()

    if mode == "auto":
        from auth.auto_auth import auto_login
        enctoken = auto_login(settings)
    elif mode == "manual":
        from auth.manual_auth import manual_login
        enctoken = manual_login(settings)
    else:
        raise ValueError(f"Unknown auth mode '{mode}'. Use 'auto' or 'manual'.")

    user_id = get(settings, "zerodha", "user_id", default="")
    save_token(enctoken, user_id)
    log("Token saved to config/enctoken.json", "ok")
    return enctoken


def get_kite(mode: Optional[str] = None, force_new: bool = False) -> KiteClient:
    """Return a working KiteClient, logging in only when needed."""
    if not force_new:
        saved = load_token()
        if saved:
            kite = KiteClient(saved["enctoken"])
            if kite.is_token_valid():
                log(f"Using saved token from {saved['generated_at']}", "ok")
                return kite
            log("Saved token has expired - logging in again", "warn")
            clear_token()

    enctoken = authenticate(mode)
    return KiteClient(enctoken)
