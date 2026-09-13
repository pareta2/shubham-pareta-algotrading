"""
auth/auto_auth.py
-----------------
AUTO mode = zero typing.  Everything comes from config/settings.json:

    user_id + password  -> from settings["zerodha"]
    2FA code            -> either read from Gmail  (twofa_method = "gmail_otp")
                           or generated with pyotp (twofa_method = "totp")

Returns the enctoken string.
"""

from datetime import datetime, timedelta

import pyotp

from auth.gmail_otp import wait_for_otp
from auth.kite_login import TWOFA_OTP, TWOFA_TOTP, KiteLoginSession
from common.logger import log
from common.settings import get


def auto_login(settings: dict) -> str:
    user_id = get(settings, "zerodha", "user_id")
    password = get(settings, "zerodha", "password")
    method = get(settings, "auth", "twofa_method", default="gmail_otp")

    if not user_id or not password:
        raise ValueError("zerodha.user_id / zerodha.password missing in config/settings.json")

    log(f"AUTO login for {user_id} using 2FA method '{method}'", "step")
    kite = KiteLoginSession()

    # ---- step 1: user id + password ------------------------------------
    kite.login(user_id, password)
    log(f"Password accepted. Zerodha says your account's 2FA type is '{kite.twofa_type_from_server}'", "ok")

    # ---- step 2 + 3: the 2FA code --------------------------------------
    if method == "totp":
        secret = get(settings, "zerodha", "totp_secret")
        if not secret:
            raise ValueError("twofa_method is 'totp' but zerodha.totp_secret is empty in settings.json")
        code = pyotp.TOTP(secret).now()
        log("Generated TOTP code from your secret", "ok")
        enctoken = kite.submit_twofa(code, TWOFA_TOTP)

    elif method == "gmail_otp":
        asked_at = datetime.now() - timedelta(seconds=30)   # small buffer for clock differences
        kite.request_otp()
        log("Asked Zerodha to send the OTP (SMS + Email)", "ok")
        code = wait_for_otp(
            gmail_email=get(settings, "gmail", "email"),
            app_password=get(settings, "gmail", "app_password"),
            folder=get(settings, "gmail", "folder", default="Inbox"),
            not_before=asked_at,
            attempts=get(settings, "auth", "otp_wait_attempts", default=10),
            wait_seconds=get(settings, "auth", "otp_wait_seconds", default=10),
        )
        log(f"OTP read from Gmail: {code}", "ok")
        enctoken = kite.submit_twofa(code, TWOFA_OTP)

    else:
        raise ValueError(f"Unknown twofa_method '{method}'. Use 'gmail_otp' or 'totp'.")

    log("2FA accepted - enctoken generated", "ok")
    return enctoken
