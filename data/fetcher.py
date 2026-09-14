"""
data/fetcher.py
---------------
Downloads candles for ONE instrument - but only the parts you do not
already have.

    fetch_missing()  1. reads the meta file  -> which date ranges are already downloaded?
                     2. subtracts them from what you asked for -> the GAPS
                     3. downloads each gap in chunks (Zerodha caps days per request)
                     4. after EVERY chunk: saves the CSV + marks that chunk as covered
                        (so if your internet drops, the next run resumes from there)

    download_range() is the lower-level "just download these dates" helper.
"""

import time
from datetime import date, datetime, timedelta
from typing import List, Tuple

import pandas as pd

from broker.kite_client import KiteClient
from common.logger import log
from data.coverage import missing_ranges, split_range
from data.databank import candles_to_dataframe, load_meta, save_candles, save_meta

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

# Today's candles are only "complete" once the market has closed.
MARKET_CLOSE_HOUR = 16
PAUSE_BETWEEN_CALLS = 0.4   # seconds - be polite to Zerodha's servers


def normalize_interval(interval: str) -> str:
    """'5m' -> '5minute',  '1d' -> 'day'.  Raises if unknown."""
    interval = interval.strip().lower()
    interval = INTERVAL_ALIASES.get(interval, interval)
    if interval not in MAX_DAYS_PER_REQUEST:
        raise ValueError(f"Unknown interval '{interval}'. Use one of: {', '.join(MAX_DAYS_PER_REQUEST)}")
    return interval


def download_range(kite: KiteClient, instrument_token: int, interval: str,
                   start: date, end: date, oi: bool = False) -> pd.DataFrame:
    """ONE request: candles from 00:00 of `start` to 23:59:59 of `end`."""
    candles = kite.historical_data(
        instrument_token,
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.max.time().replace(microsecond=0)),
        interval, oi=oi,
    )
    time.sleep(PAUSE_BETWEEN_CALLS)
    return candles_to_dataframe(candles)


def _complete_through(chunk_end: date) -> date:
    """
    Up to which day can we call this chunk 'fully downloaded'?
    Everything, except: today is complete only after market close.
    """
    today = date.today()
    if chunk_end >= today and datetime.now().hour < MARKET_CLOSE_HOUR:
        return today - timedelta(days=1)
    return chunk_end


def fetch_missing(kite: KiteClient, instrument: dict, interval: str,
                  start: date, end: date, oi: bool = False, force: bool = False) -> int:
    """
    Download only what is missing between `start` and `end` for this instrument.
    Returns the number of candles downloaded.

    instrument : dict from data.instruments.find_instrument()
    force      : ignore the meta file and download the whole range again
    """
    interval = normalize_interval(interval)
    symbol, exchange = instrument["tradingsymbol"], instrument["exchange"]
    token = int(instrument["instrument_token"])

    meta = load_meta(symbol, interval, exchange)
    gaps: List[Tuple[date, date]] = [(start, end)] if force else missing_ranges(meta["covered"], (start, end))

    if not gaps:
        log(f"{symbol} {interval}: {start} -> {end} is already in the DataBank. Nothing to download.", "ok")
        return 0

    if meta["covered"] and not force:
        have = ", ".join(f"{a}..{b}" for a, b in meta["covered"])
        need = ", ".join(f"{a}..{b}" for a, b in gaps)
        log(f"{symbol} {interval}: already have [{have}]", "info")
        log(f"{symbol} {interval}: downloading only [{need}]", "step")
    else:
        log(f"{symbol} {interval}: downloading {start} -> {end}", "step")

    total = 0
    for gap_start, gap_end in gaps:
        for chunk_start, chunk_end in split_range(gap_start, gap_end, MAX_DAYS_PER_REQUEST[interval]):
            log(f"  chunk {chunk_start} -> {chunk_end}")
            df = download_range(kite, token, interval, chunk_start, chunk_end, oi=oi)
            if not df.empty:
                save_candles(df, symbol, interval, exchange)
                total += len(df)
            done_through = _complete_through(chunk_end)
            if done_through >= chunk_start:
                meta["covered"].append((chunk_start, done_through))
                save_meta(meta, symbol, interval, exchange)      # progress is safe on disk

    log(f"{symbol} {interval}: {total:,} new candles saved", "ok")
    return total
