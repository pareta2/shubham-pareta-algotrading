"""
data/instruments.py
-------------------
Zerodha identifies every stock / index / option by a NUMBER called the
*instrument_token*.  Humans use names like "RELIANCE".  This file converts
names -> tokens.

Zerodha publishes the full list (about 1 lakh rows) as a public CSV every
morning at  https://api.kite.trade/instruments  (no login needed).
We download it once a day into  data/DataBank/instruments.csv  and search it.
"""

from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from common.logger import log
from data.databank import DATABANK_DIR

INSTRUMENTS_URL = "https://api.kite.trade/instruments"
INSTRUMENTS_FILE = DATABANK_DIR / "instruments.csv"

# Friendly names people type  ->  the exact name Zerodha uses (all on NSE except SENSEX)
INDEX_ALIASES = {
    "NIFTY": ("NSE", "NIFTY 50"),
    "NIFTY50": ("NSE", "NIFTY 50"),
    "BANKNIFTY": ("NSE", "NIFTY BANK"),
    "FINNIFTY": ("NSE", "NIFTY FIN SERVICE"),
    "MIDCPNIFTY": ("NSE", "NIFTY MID SELECT"),
    "SENSEX": ("BSE", "SENSEX"),
    "BANKEX": ("BSE", "BANKEX"),
    "INDIAVIX": ("NSE", "INDIA VIX"),
}


def download_instruments() -> pd.DataFrame:
    """Download the fresh list from Zerodha and save it as CSV."""
    log("Downloading instrument list from Zerodha (takes a few seconds)...", "step")
    response = requests.get(INSTRUMENTS_URL, timeout=60)
    response.raise_for_status()
    INSTRUMENTS_FILE.write_text(response.text, encoding="utf-8")
    df = pd.read_csv(INSTRUMENTS_FILE)
    log(f"Saved {len(df):,} instruments to {INSTRUMENTS_FILE.name}", "ok")
    return df


def load_instruments(refresh: bool = False) -> pd.DataFrame:
    """Use today's cached CSV if we have it, otherwise download."""
    if refresh or not INSTRUMENTS_FILE.exists():
        return download_instruments()
    modified = datetime.fromtimestamp(INSTRUMENTS_FILE.stat().st_mtime)
    if modified.date() < datetime.today().date():
        log("Instrument list is from an earlier day - refreshing", "info")
        return download_instruments()
    return pd.read_csv(INSTRUMENTS_FILE)


def find_instrument(symbol: str, exchange: str = "NSE") -> Optional[dict]:
    """
    Find one instrument by trading symbol.   find_instrument("RELIANCE")
    Also understands index nicknames:         find_instrument("BANKNIFTY")
    Returns a dict (instrument_token, tradingsymbol, exchange, ...) or None.
    """
    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()

    if symbol in INDEX_ALIASES:
        exchange, symbol = INDEX_ALIASES[symbol]

    df = load_instruments()
    match = df[(df["tradingsymbol"] == symbol) & (df["exchange"] == exchange)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def search_instruments(text: str, exchange: Optional[str] = None, limit: int = 30) -> pd.DataFrame:
    """Search by partial symbol or company name.  search_instruments("RELIANCE", "NFO")"""
    df = load_instruments()
    text = text.upper()
    mask = df["tradingsymbol"].str.upper().str.contains(text, na=False) | \
           df["name"].astype(str).str.upper().str.contains(text, na=False)
    if exchange:
        mask &= df["exchange"] == exchange.upper()
    columns = ["instrument_token", "tradingsymbol", "name", "exchange", "segment",
               "instrument_type", "expiry", "strike", "lot_size"]
    return df.loc[mask, columns].head(limit)
