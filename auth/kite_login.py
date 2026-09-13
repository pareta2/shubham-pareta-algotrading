"""
auth/kite_login.py
------------------
The raw conversation with Zerodha's login server.  Both AUTO and MANUAL
modes use this file - the only difference is *where the 2FA code comes from*.

Zerodha login = 3 HTTP calls:

    1. login(user_id, password)          -> gives us a request_id
    2. request_otp(...)                  -> (only for SMS/Email OTP) tells Zerodha "send the OTP now"
    3. submit_twofa(request_id, code)    -> returns the enctoken cookie

Nothing in this file reads Gmail or opens a browser.  Keep it that way, so it
stays easy to understand.
"""

import requests

KITE_URL = "https://kite.zerodha.com"

# Pretend to be a normal browser (Zerodha rejects requests without a User-Agent)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": KITE_URL + "/",
}

# The two kinds of 2FA Zerodha supports
TWOFA_TOTP = "totp"   # 6-digit code from an authenticator app (Google Authenticator etc.)
TWOFA_OTP = "sms"     # 6-digit OTP that Zerodha sends on SMS + Email


class KiteLoginError(Exception):
    """Raised when Zerodha says no (wrong password, wrong OTP, blocked, ...)."""


class KiteLoginSession:
    """
    Keeps ONE requests.Session for the whole login, so cookies given by
    Zerodha in step 1 are automatically sent back in steps 2 and 3.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)
        # Step 0: visit the home page once so Zerodha sets its initial cookies
        self.session.get(KITE_URL, timeout=15)
        self.request_id = None
        self.user_id = None
        self.twofa_type_from_server = None   # Zerodha tells us which 2FA the account uses

    # ------------------------------------------------------------------ #
    def _check(self, response: requests.Response, step: str) -> dict:
        """Turn a bad Zerodha reply into a readable KiteLoginError."""
        try:
            body = response.json()
        except ValueError:
            raise KiteLoginError(f"{step}: unexpected reply (HTTP {response.status_code})")
        if response.status_code != 200 or body.get("status") != "success":
            raise KiteLoginError(f"{step}: {body.get('message', 'unknown error')}")
        return body.get("data", {})

    # ------------------------------------------------------------------ #
    def login(self, user_id: str, password: str) -> str:
        """Step 1 - send user id + password.  Returns request_id."""
        response = self.session.post(
            f"{KITE_URL}/api/login",
            data={"user_id": user_id, "password": password, "type": "user_id"},
            timeout=15,
        )
        data = self._check(response, "Login (step 1)")
        self.user_id = user_id
        self.request_id = data["request_id"]
        self.twofa_type_from_server = data.get("twofa_type")   # e.g. "totp" or "app_code"
        return self.request_id

    # ------------------------------------------------------------------ #
    def request_otp(self) -> None:
        """Step 2 - ask Zerodha to send the OTP by SMS + Email.  Skip this for TOTP."""
        response = self.session.post(
            f"{KITE_URL}/oms/trusted/kitefront/user/{self.user_id}/twofa/generate_otp",
            data={"request_id": self.request_id, "twofa_type": TWOFA_OTP},
            timeout=15,
        )
        self._check(response, "Request OTP (step 2)")

    # ------------------------------------------------------------------ #
    def submit_twofa(self, code: str, twofa_type: str) -> str:
        """Step 3 - send the 6-digit code.  Returns the enctoken."""
        response = self.session.post(
            f"{KITE_URL}/api/twofa",
            data={
                "user_id": self.user_id,
                "request_id": self.request_id,
                "twofa_type": twofa_type,
                "twofa_value": code.strip(),
                "skip_session": "",
            },
            timeout=15,
        )
        self._check(response, "2FA (step 3)")
        enctoken = response.cookies.get("enctoken") or self.session.cookies.get("enctoken")
        if not enctoken:
            raise KiteLoginError("2FA accepted but no enctoken cookie came back.")
        return enctoken
