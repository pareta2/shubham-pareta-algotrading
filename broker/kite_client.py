"""
broker/kite_client.py
---------------------
A very small wrapper around Zerodha Kite's web API using the *enctoken*.

The enctoken is the same token your browser uses after you log in at
kite.zerodha.com.  Sending it in the "Authorization" header lets us call
the same endpoints the Kite website calls.

For now this class only has what the AUTH module needs (profile + margins).
The DATA module will add historical_data(), ltp(), instruments() etc. here.
"""

import requests

KITE_API = "https://kite.zerodha.com/oms"


class KiteClient:
    def __init__(self, enctoken: str):
        self.enctoken = enctoken
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"enctoken {enctoken}",
            "User-Agent": "Mozilla/5.0",
        })

    # ------------------------------------------------------------------ #
    # internal helper: GET a url and return the "data" part of the JSON
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: dict = None) -> dict:
        response = self.session.get(f"{KITE_API}{path}", params=params, timeout=15)
        body = response.json()
        if response.status_code != 200 or body.get("status") != "success":
            raise Exception(f"Kite API error {response.status_code}: {body.get('message', body)}")
        return body["data"]

    # ------------------------------------------------------------------ #
    # public methods
    # ------------------------------------------------------------------ #
    def profile(self) -> dict:
        """Your account details (name, email, user_id, ...)."""
        return self._get("/user/profile")

    def margins(self) -> dict:
        """Available cash / margins for equity and commodity."""
        return self._get("/user/margins")

    def is_token_valid(self) -> bool:
        """True if the enctoken still works, False if expired / wrong."""
        try:
            self.profile()
            return True
        except Exception:
            return False
