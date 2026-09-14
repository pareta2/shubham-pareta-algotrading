"""
data/verify.py
--------------
Health-check for one CSV in the DataBank:

    * which date ranges the meta file says are downloaded
    * weekdays inside those ranges that have NO candles     (usually holidays)
    * days that have far FEWER candles than a normal day    (partial download?)

With --fix, each suspicious day is downloaded again ONCE and then remembered
in the meta file ("rechecked_days"), so a real holiday or a half-day session
is never re-downloaded again and again.
"""

from datetime import date
from typing import List

import pandas as pd

from common.logger import log
from data.coverage import days_to_ranges
from data.databank import load_candles, load_meta, save_candles, save_meta

PARTIAL_DAY_RATIO = 0.8    # a day with < 80% of the usual candle count looks partial


def find_problems(symbol: str, interval: str, exchange: str = "NSE") -> dict:
    """Returns {'empty_days': [...], 'partial_days': [...], 'typical_candles': n, ...}"""
    df = load_candles(symbol, interval, exchange)
    meta = load_meta(symbol, interval, exchange)
    result = {"covered": meta["covered"], "rechecked": meta["rechecked_days"],
              "rows": 0, "empty_days": [], "partial_days": [], "typical_candles": 0}
    if df is None or df.empty:
        return result

    result["rows"] = len(df)
    per_day = df.groupby(df["date"].dt.date).size()
    have_days = set(per_day.index)
    already = set(meta["rechecked_days"])

    # 1. weekdays inside covered ranges with no candles at all
    for start, end in meta["covered"]:
        for day in pd.date_range(start, end, freq="B").date:     # "B" = business days (Mon-Fri)
            if day not in have_days and day not in already:
                result["empty_days"].append(day)

    # 2. days with far fewer candles than usual (only makes sense for intraday data)
    if interval != "day" and len(per_day) >= 5:
        typical = int(per_day.median())
        result["typical_candles"] = typical
        for day, count in per_day.items():
            if count < typical * PARTIAL_DAY_RATIO and day not in already:
                result["partial_days"].append((day, int(count)))
    return result


def print_report(symbol: str, interval: str, problems: dict) -> None:
    print(f"\n📋 {symbol} {interval}")
    print(f"   candles   : {problems['rows']:,}")
    print("   covered   : " + (", ".join(f"{a}..{b}" for a, b in problems["covered"]) or "(nothing)"))
    if problems["typical_candles"]:
        print(f"   usual day : {problems['typical_candles']} candles")
    empty, partial = problems["empty_days"], problems["partial_days"]
    print(f"   empty weekdays  : {len(empty)}  " + (f"(e.g. {', '.join(str(d) for d in empty[:5])} ...)" if empty else "✔"))
    print(f"   partial days    : {len(partial)}  " + (f"(e.g. {', '.join(f'{d}={n}' for d, n in partial[:5])} ...)" if partial else "✔"))
    if problems["rechecked"]:
        print(f"   already re-checked once: {len(problems['rechecked'])} days (holidays / half-days)")
    if empty or partial:
        print("   ➜ run again with --fix to re-download these days once")


def fix_problems(kite, instrument: dict, interval: str, problems: dict) -> int:
    """Re-download every suspicious day once.  Returns candles added."""
    from data.fetcher import download_range

    symbol, exchange = instrument["tradingsymbol"], instrument["exchange"]
    days: List[date] = sorted(set(problems["empty_days"]) | {d for d, _ in problems["partial_days"]})
    if not days:
        return 0

    meta = load_meta(symbol, interval, exchange)
    added = 0
    for start, end in days_to_ranges(days):           # consecutive days -> one request
        log(f"  re-downloading {start} -> {end}")
        df = download_range(kite, int(instrument["instrument_token"]), interval, start, end)
        if not df.empty:
            save_candles(df, symbol, interval, exchange)
            added += len(df)
    meta["rechecked_days"].extend(days)
    save_meta(meta, symbol, interval, exchange)
    log(f"{symbol} {interval}: re-checked {len(days)} days, {added:,} candles added/updated", "ok")
    return added
