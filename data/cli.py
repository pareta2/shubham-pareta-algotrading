"""
data/cli.py
-----------
The `python main.py data ...` commands.  Each command is one small function.

    data fetch  --symbol RELIANCE --interval 5minute --days 30
    data fetch  --symbol NIFTY BANKNIFTY --interval day --from 2024-01-01 --to 2024-12-31
    data search RELIANCE --exchange NFO
    data list
    data verify --symbol RELIANCE --interval 5minute [--fix]
    data ltp    --symbol RELIANCE INFY
"""

from datetime import date, datetime, timedelta

import pandas as pd

from common.logger import log


# ------------------------------------------------------------------ fetch
def _date_range(args):
    """--from/--to  or  --days  ->  (start_date, end_date)"""
    end = datetime.strptime(args.to, "%Y-%m-%d").date() if args.to else date.today()
    if args.__dict__["from"]:
        start = datetime.strptime(args.__dict__["from"], "%Y-%m-%d").date()
    else:
        start = end - timedelta(days=args.days)
    return start, end


def cmd_fetch(args):
    from auth import get_kite
    from data.fetcher import fetch_missing, normalize_interval
    from data.instruments import find_instrument

    interval = normalize_interval(args.interval)
    start, end = _date_range(args)

    kite = get_kite()
    for symbol in args.symbol:
        instrument = find_instrument(symbol, args.exchange)
        if instrument is None:
            log(f"'{symbol}' not found on {args.exchange}. Try:  python main.py data search {symbol}", "error")
            continue
        fetch_missing(kite, instrument, interval, start, end, oi=args.oi, force=args.force)


# ----------------------------------------------------------------- verify
def cmd_verify(args):
    from data.fetcher import normalize_interval
    from data.instruments import find_instrument
    from data.verify import find_problems, fix_problems, print_report

    interval = normalize_interval(args.interval)
    kite = None
    for symbol in args.symbol:
        instrument = find_instrument(symbol, args.exchange)
        if instrument is None:
            log(f"'{symbol}' not found on {args.exchange}", "error")
            continue
        problems = find_problems(instrument["tradingsymbol"], interval, instrument["exchange"])
        print_report(instrument["tradingsymbol"], interval, problems)
        if args.fix and (problems["empty_days"] or problems["partial_days"]):
            if kite is None:
                from auth import get_kite
                kite = get_kite()
            fix_problems(kite, instrument, interval, problems)


# ----------------------------------------------------------------- search
def cmd_search(args):
    from data.instruments import search_instruments

    df = search_instruments(args.text, args.exchange, limit=args.limit)
    if df.empty:
        log(f"Nothing matched '{args.text}'", "warn")
        return
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(df.to_string(index=False))


# ------------------------------------------------------------------- list
def cmd_list(args):
    from data.databank import DATABANK_DIR, list_databank

    df = list_databank()
    if df.empty:
        log(f"DataBank is empty ({DATABANK_DIR}). Fetch something first!", "warn")
        return
    print(df.to_string(index=False))


# -------------------------------------------------------------------- ltp
def cmd_ltp(args):
    from auth import get_kite
    from data.instruments import INDEX_ALIASES

    keys = []
    for symbol in args.symbol:
        symbol = symbol.upper()
        exchange, name = INDEX_ALIASES.get(symbol, (args.exchange.upper(), symbol))
        keys.append(f"{exchange}:{name}")
    prices = get_kite().ltp(keys)
    for key, info in prices.items():
        print(f"  {key:<28} {info['last_price']}")


# --------------------------------------------------------------- register
def register(subparsers):
    """Called by main.py to plug the `data` commands into the CLI."""
    data = subparsers.add_parser("data", help="download candles into data/DataBank (CSV)")
    sub = data.add_subparsers(dest="data_command")

    f = sub.add_parser("fetch", help="download candles for one or more symbols")
    f.add_argument("--symbol", nargs="+", required=True, help="RELIANCE  or  NIFTY BANKNIFTY  or  NIFTY25SEP24500CE")
    f.add_argument("--exchange", default="NSE", help="NSE (default), BSE, NFO, BFO, MCX, CDS")
    f.add_argument("--interval", default="5minute", help="minute 3minute 5minute 10minute 15minute 30minute 60minute day (or 5m, 1h, 1d)")
    f.add_argument("--days", type=int, default=30, help="how many days back from today (default 30)")
    f.add_argument("--from", help="start date YYYY-MM-DD (overrides --days)")
    f.add_argument("--to", help="end date YYYY-MM-DD (default today)")
    f.add_argument("--oi", action="store_true", help="also fetch open interest (F&O only)")
    f.add_argument("--force", action="store_true", help="re-download everything, ignoring what is already there")
    f.set_defaults(func=cmd_fetch)

    v = sub.add_parser("verify", help="check a CSV for missing / partial days (add --fix to repair)")
    v.add_argument("--symbol", nargs="+", required=True)
    v.add_argument("--exchange", default="NSE")
    v.add_argument("--interval", default="5minute")
    v.add_argument("--fix", action="store_true", help="re-download suspicious days (once)")
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("search", help="search the instrument list")
    s.add_argument("text", help="part of a symbol or company name")
    s.add_argument("--exchange", help="limit to one exchange, e.g. NFO")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_search)

    l = sub.add_parser("list", help="show what is in the DataBank")
    l.set_defaults(func=cmd_list)

    p = sub.add_parser("ltp", help="last traded price (quick check that login works)")
    p.add_argument("--symbol", nargs="+", required=True)
    p.add_argument("--exchange", default="NSE")
    p.set_defaults(func=cmd_ltp)

    data.set_defaults(func=lambda args: data.print_help())
