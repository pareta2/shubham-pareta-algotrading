"""
broker/kite_client.py
---------------------
A very small wrapper around Zerodha's Kite API.  ONE class, TWO ways to log in:

  1. API KEY  (official Kite Connect - RECOMMENDED)
        base url : https://api.kite.trade
        header   : Authorization: token <api_key>:<access_token>

  2. ENCTOKEN (the cookie your browser gets on kite.zerodha.com - unofficial)
        base url : https://kite.zerodha.com/oms
        header   : Authorization: enctoken <enctoken>

The endpoint PATHS after the base url are the same for both
(/user/profile, /orders/regular, /instruments/historical/... etc.), so the
rest of the project never needs to know which one you used.

Methods:
    profile(), margins()                         -> used by AUTH
    ltp(), quote(), historical_data()            -> used by DATA
"""

from datetime import datetime
from typing import List, Optional, Union

import requests

KITE_CONNECT_API = "https://api.kite.trade"          # official, needs api_key + access_token
KITE_WEB_API = "https://kite.zerodha.com/oms"        # unofficial, needs enctoken


class KiteClient:
    def __init__(self, enctoken: Optional[str] = None,
                 api_key: Optional[str] = None, access_token: Optional[str] = None):
        self.session = requests.Session()
        if api_key and access_token:
            self.auth_type = "api_key"
            self.root = KITE_CONNECT_API
            self.session.headers.update({
                "X-Kite-Version": "3",
                "Authorization": f"token {api_key}:{access_token}",
            })
        elif enctoken:
            self.auth_type = "enctoken"
            self.root = KITE_WEB_API
            self.session.headers.update({
                "Authorization": f"enctoken {enctoken}",
                "User-Agent": "Mozilla/5.0",
            })
        else:
            raise ValueError("KiteClient needs either enctoken=... or api_key=... + access_token=...")

    @classmethod
    def from_session(cls, saved: dict) -> "KiteClient":
        """Build a client from the dict stored in config/session.json."""
        if saved.get("auth_type") == "api_key":
            return cls(api_key=saved["api_key"], access_token=saved["access_token"])
        return cls(enctoken=saved["enctoken"])

    # ------------------------------------------------------------------ #
    # internal helper: GET a url and return the "data" part of the JSON
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: dict = None) -> dict:
        response = self.session.get(f"{self.root}{path}", params=params, timeout=15)
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

    def ltp(self, instruments: Union[str, List[str]]) -> dict:
        """
        Last traded price.  instruments = "NSE:RELIANCE" or ["NSE:RELIANCE", "NSE:INFY"]
        Returns {"NSE:RELIANCE": {"instrument_token": ..., "last_price": ...}, ...}
        """
        return self._get("/quote/ltp", params={"i": instruments})

    def quote(self, instruments: Union[str, List[str]]) -> dict:
        """Full quote (ohlc, volume, depth, oi ...) for one or more instruments."""
        return self._get("/quote", params={"i": instruments})

    def historical_data(self, instrument_token: int, from_date: datetime, to_date: datetime,
                        interval: str, oi: bool = False, continuous: bool = False) -> list:
        """
        Candles between two dates.  ONE request only - Zerodha caps how many days
        one request may cover, so data/fetcher.py calls this in chunks.

        interval : minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day
        Returns  : [ {date, open, high, low, close, volume[, oi]}, ... ]
        """
        params = {
            "from": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "to": to_date.strftime("%Y-%m-%d %H:%M:%S"),
            "oi": 1 if oi else 0,
            "continuous": 1 if continuous else 0,
        }
        data = self._get(f"/instruments/historical/{instrument_token}/{interval}", params=params)
        candles = []
        for row in data.get("candles", []):
            candle = {"date": row[0], "open": row[1], "high": row[2],
                      "low": row[3], "close": row[4], "volume": row[5]}
            if oi and len(row) > 6:
                candle["oi"] = row[6]
            candles.append(candle)
        return candles

    def is_token_valid(self) -> bool:
        """True if the enctoken still works, False if expired / wrong."""
        try:
            self.profile()
            return True
        except Exception:
            return False
