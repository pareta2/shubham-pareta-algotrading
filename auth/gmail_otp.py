"""
auth/gmail_otp.py
-----------------
Reads the Kite OTP email from your Gmail inbox using IMAP.

Zerodha sends an email like:
    From:    noreply@alertsmailer.zerodha.net
    Subject: 123456 is your Kite 2FA OTP

We log in to Gmail with an *App Password* (NOT your normal Gmail password),
find the newest such email that arrived AFTER we asked for the OTP, and pull
the 6 digits out of the subject line.

See README -> "Gmail setup" for how to create an App Password.
"""

import email
import imaplib
import re
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import mktime_tz, parsedate_tz
from typing import Optional

from common.logger import log

IMAP_SERVER = "imap.gmail.com"
ZERODHA_SENDER = "noreply@alertsmailer.zerodha.net"
SUBJECT_MARKER = "is your Kite 2FA OTP"


def _subject_of(msg) -> str:
    raw, encoding = decode_header(msg.get("Subject", ""))[0]
    if isinstance(raw, bytes):
        raw = raw.decode(encoding or "utf-8", errors="ignore")
    return raw


def _received_at(msg) -> Optional[datetime]:
    parsed = parsedate_tz(msg.get("Date"))
    if not parsed:
        return None
    return datetime.fromtimestamp(mktime_tz(parsed))


def read_otp(gmail_email: str, app_password: str, folder: str = "Inbox",
             not_before: Optional[datetime] = None) -> Optional[str]:
    """
    Look ONCE in Gmail.  Returns the OTP string, or None if not there yet.

    not_before : ignore emails older than this (so an old OTP from this
                 morning is never picked by mistake).
    """
    if not_before is None:
        not_before = datetime.now() - timedelta(minutes=2)

    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        imap.login(gmail_email, app_password)
        status, _ = imap.select(f'"{folder}"', readonly=True)
        if status != "OK":
            log(f"Could not open Gmail folder '{folder}'", "error")
            return None

        today = datetime.today().strftime("%d-%b-%Y")
        status, result = imap.search(None, f'SINCE {today}', "FROM", f'"{ZERODHA_SENDER}"')
        if status != "OK" or not result[0]:
            return None

        # newest emails last -> walk backwards
        for email_id in reversed(result[0].split()):
            _, parts = imap.fetch(email_id, "(RFC822)")
            for part in parts:
                if not isinstance(part, tuple):
                    continue
                msg = email.message_from_bytes(part[1])
                subject = _subject_of(msg)
                received = _received_at(msg)
                if SUBJECT_MARKER not in subject:
                    continue
                if received and received < not_before:
                    continue          # too old, keep looking
                digits = re.findall(r"\d{4,8}", subject)
                if digits:
                    log(f"Found OTP email received at {received}", "ok")
                    return digits[0]
        return None
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()


def wait_for_otp(gmail_email: str, app_password: str, folder: str = "Inbox",
                 not_before: Optional[datetime] = None,
                 attempts: int = 10, wait_seconds: int = 10) -> str:
    """
    Keep checking Gmail every `wait_seconds` until the OTP arrives
    (max `attempts` times).  Raises if it never shows up.
    """
    for attempt in range(1, attempts + 1):
        log(f"Waiting {wait_seconds}s for the OTP email... (try {attempt}/{attempts})")
        time.sleep(wait_seconds)
        otp = read_otp(gmail_email, app_password, folder, not_before)
        if otp:
            return otp
    raise TimeoutError(
        f"OTP email did not arrive in {attempts * wait_seconds} seconds. "
        "Check: Gmail app password, IMAP enabled, and that Zerodha sends OTP to this email."
    )
