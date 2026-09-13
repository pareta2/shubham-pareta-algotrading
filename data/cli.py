"""
data/cli.py
-----------
The `python main.py data ...` commands.  Each command is one small function.

    data fetch  --symbol RELIANCE --interval 5minute --days 30
    data fetch  --symbol NIFTY BANKNIFTY --interval day --from 2024-01-01 --to 2024-12-31
    data search RELIANCE --exchange NFO
    data list
    data ltp    --symbol RELIANCE INFY
"""

from datetime import datetime, timedelta

import pandas as pd

from common.logger import log


# ------------------------------------------------------------------ fetch
def cmd_fetch(args):
    from auth import get_kite
    from data.databank import save_candles
    from data.fetcher import fetch_candles, normalize_interval
    from data.instruments import find_instrument

    interval = normalize_interval(args.interval)

    # work out the date range: either --from/--to or --days
    to_date = datetime.strptime(args.to, "%Y-%m-%d") if args.to else datetime.now()
    if args.__dict__["from"]:
        from_date = datetime.strptime(args.__dict__["from"], "%Y-%m-%d")
    else:
        from_date = to_date - timedelta(days=args.days)
    # whole days: from 00:00:00 of the first day to 23:59:59 of the last day
    from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
    to_date = to_date.replace(hour=23, minute=59, second=59, microsecond=0)

    kite = get_kite()
    for symbol in args.symbol:
        instrument = find_instrument(symbol, args.exchange)
        if instrument is None:
            log(f"'{symbol}' not found on {args.exchange}. Try:  python main.py data search {symbol}", "error")
            continue

        log(f"Fetching {instrument['tradingsymbol']} ({instrument['exchange']}) "
            f"{interval} candles  {from_date.date()} -> {to_date.date()}", "step")
        df = fetch_candles(kite, int(instrument["instrument_token"]), interval,
                           from_date, to_date, oi=args.oi)
        if df.empty:
            log(f"No candles returned for {symbol}", "warn")
            continue
        path = save_candles(df, instrument["tradingsymbol"], interval, instrument["exchange"])
        log(f"{len(df):,} candles fetched -> {path.name}", "ok")


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
    f.set_defaults(func=cmd_fetch)

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
