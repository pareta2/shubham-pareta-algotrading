"""
data/databank.py
----------------
The DataBank is just a folder of CSV files - one file per symbol + interval:

    data/DataBank/NSE_RELIANCE_5minute.csv
    data/DataBank/NSE_NIFTY_50_day.csv

Columns:  date, open, high, low, close, volume [, oi]

Fetching the same symbol again MERGES new candles into the existing file
(no duplicates), so you can top-up your data every day.

Next to every CSV there is a small "meta" file, e.g.
    data/DataBank/NSE_RELIANCE_5minute.meta.json
It remembers which DATE RANGES have already been downloaded, so the next
fetch downloads only what is missing (see data/coverage.py).
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from data.coverage import merge_ranges

from common.settings import ROOT

DATABANK_DIR = ROOT / "data" / "DataBank"
DATABANK_DIR.mkdir(parents=True, exist_ok=True)


def csv_path(symbol: str, interval: str, exchange: str = "NSE") -> Path:
    """Where the CSV for this symbol/interval lives."""
    safe_symbol = symbol.strip().upper().replace(" ", "_").replace("/", "_")
    return DATABANK_DIR / f"{exchange.upper()}_{safe_symbol}_{interval}.csv"


def candles_to_dataframe(candles: list) -> pd.DataFrame:
    """List of candle dicts (from KiteClient) -> clean DataFrame."""
    df = pd.DataFrame(candles)
    if df.empty:
        return df
    # Zerodha gives "2024-02-01T09:15:00+0530"; keep it as plain IST time
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df


def save_candles(df: pd.DataFrame, symbol: str, interval: str, exchange: str = "NSE") -> Path:
    """Merge `df` into the CSV for this symbol (creates the file if needed)."""
    path = csv_path(symbol, interval, exchange)
    if path.exists():
        old = pd.read_csv(path, parse_dates=["date"])
        df = pd.concat([old, df], ignore_index=True)
    df = df.drop_duplicates(subset="date", keep="last").sort_values("date").reset_index(drop=True)
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return path


# ------------------------------------------------------------------ meta
def meta_path(symbol: str, interval: str, exchange: str = "NSE") -> Path:
    return csv_path(symbol, interval, exchange).with_suffix(".meta.json")


def _to_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def load_meta(symbol: str, interval: str, exchange: str = "NSE") -> dict:
    """
    Returns {"covered": [(date, date), ...], "rechecked_days": [date, ...]}.

    If the CSV exists but the meta file does not (old download or a file you
    copied in by hand) we ASSUME everything between its first and last date
    was downloaded - a sensible guess that `data verify` can double-check.
    """
    path = meta_path(symbol, interval, exchange)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            "covered": [(_to_date(a), _to_date(b)) for a, b in raw.get("covered", [])],
            "rechecked_days": [_to_date(d) for d in raw.get("rechecked_days", [])],
        }
    meta = {"covered": [], "rechecked_days": []}
    df = load_candles(symbol, interval, exchange)
    if df is not None and not df.empty:
        first, last = df["date"].min().date(), df["date"].max().date()
        meta["covered"] = [(first, last)]
        save_meta(meta, symbol, interval, exchange)
    return meta


def save_meta(meta: dict, symbol: str, interval: str, exchange: str = "NSE") -> None:
    meta["covered"] = merge_ranges(meta["covered"])
    raw = {
        "covered": [[a.isoformat(), b.isoformat()] for a, b in meta["covered"]],
        "rechecked_days": sorted(d.isoformat() for d in set(meta["rechecked_days"])),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_path(symbol, interval, exchange).write_text(json.dumps(raw, indent=2), encoding="utf-8")


def load_candles(symbol: str, interval: str, exchange: str = "NSE") -> Optional[pd.DataFrame]:
    """Read a CSV from the DataBank.  Returns None if it does not exist."""
    path = csv_path(symbol, interval, exchange)
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["date"])


def list_databank() -> pd.DataFrame:
    """One row per CSV: file, rows, first date, last date."""
    rows = []
    for path in sorted(DATABANK_DIR.glob("*.csv")):
        if path.name == "instruments.csv":
            continue
        df = pd.read_csv(path, usecols=["date"])
        meta = path.with_suffix(".meta.json")
        covered = json.loads(meta.read_text()).get("covered", []) if meta.exists() else []
        rows.append({
            "file": path.name,
            "rows": len(df),
            "first": df["date"].iloc[0] if len(df) else "",
            "last": df["date"].iloc[-1] if len(df) else "",
            "covered_ranges": " | ".join(f"{a}..{b}" for a, b in covered) or "(no meta)",
        })
    return pd.DataFrame(rows, columns=["file", "rows", "first", "last", "covered_ranges"])
