"""
data/fetcher.py
---------------
Downloads candles for ONE instrument between two dates.

Zerodha allows only a limited number of days per request (e.g. 60 days of
1-minute candles).  So we slice the date range into chunks, ask for each
chunk, and glue the pieces together.  That is all this file does.
"""

import time
from datetime import datetime, timedelta

import pandas as pd

from broker.kite_client import KiteClient
from common.logger import log
from data.databank import candles_to_dataframe

# Zerodha's "max days per request" for each candle size
MAX_DAYS_PER_REQUEST = {
    "minute": 60,
    "3minute": 100,
    "5minute": 100,
    "10minute": 100,
    "15minute": 200,
    "30minute": 200,
    "60minute": 400,
    "day": 2000,
}

# Friendly names people type -> what Zerodha expects
INTERVAL_ALIASES = {
    "1m": "minute", "1min": "minute", "1minute": "minute",
    "3m": "3minute", "5m": "5minute", "10m": "10minute",
    "15m": "15minute", "30m": "30minute",
    "1h": "60minute", "60m": "60minute", "hour": "60minute",
    "1d": "day", "d": "day", "daily": "day",
}


def normalize_interval(interval: str) -> str:
    """'5m' -> '5minute',  '1d' -> 'day'.  Raises if unknown."""
    interval = interval.strip().lower()
    interval = INTERVAL_ALIASES.get(interval, interval)
    if interval not in MAX_DAYS_PER_REQUEST:
        raise ValueError(f"Unknown interval '{interval}'. Use one of: {', '.join(MAX_DAYS_PER_REQUEST)}")
    return interval


def fetch_candles(kite: KiteClient, instrument_token: int, interval: str,
                  from_date: datetime, to_date: datetime, oi: bool = False,
                  pause_seconds: float = 0.4) -> pd.DataFrame:
    """
    Download all candles from `from_date` to `to_date` (chunk by chunk)
    and return one DataFrame sorted by date.
    """
    interval = normalize_interval(interval)
    max_days = MAX_DAYS_PER_REQUEST[interval]

    all_candles = []
    chunk_start = from_date
    chunk_no = 0
    while chunk_start <= to_date:
        chunk_end = min(chunk_start + timedelta(days=max_days), to_date)
        chunk_no += 1
        log(f"  chunk {chunk_no}: {chunk_start.date()} -> {chunk_end.date()}")
        candles = kite.historical_data(instrument_token, chunk_start, chunk_end, interval, oi=oi)
        all_candles.extend(candles)
        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(pause_seconds)          # be polite to Zerodha's servers

    df = candles_to_dataframe(all_candles)
    if not df.empty:
        df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
    return df
