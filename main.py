"""
main.py  -  the front door of the project
=========================================

Run everything from here.  Examples:

    python main.py auth                  # login using mode from settings.json
    python main.py auth --mode api_key   # official Kite Connect API key (recommended)
    python main.py auth --mode manual    # enctoken via browser page (unofficial)
    python main.py auth --mode auto      # enctoken, fully automatic (unofficial)
    python main.py auth --enctoken XXX   # I already have an enctoken, just save it
    python main.py auth --check          # is my saved token still valid?
    python main.py auth --force          # ignore saved token, login again

    python main.py data fetch --symbol RELIANCE --interval 5minute --days 30
    python main.py data search RELIANCE
    python main.py data list

Coming next:
    python main.py backtest ...
    python main.py live ...
"""

import argparse
import os
import sys


def cmd_auth(args):
    from auth import authenticate, get_kite, save_enctoken
    from auth.token_store import load_session
    from broker.kite_client import KiteClient
    from common.logger import log

    if args.enctoken:
        # you already copied the enctoken from the browser - no login flow at all
        saved = save_enctoken(args.enctoken)
        kite = KiteClient.from_session(saved)
        if not kite.is_token_valid():
            log("That enctoken was rejected by Zerodha (expired or mistyped).", "error")
            return
    elif args.check:
        saved = load_session()
        if not saved:
            log("No saved session. Run:  python main.py auth", "warn")
            return
        if KiteClient.from_session(saved).is_token_valid():
            log(f"{saved.get('auth_type')} session from {saved['generated_at']} is VALID ✔", "ok")
        else:
            log(f"Session from {saved['generated_at']} has EXPIRED. Run:  python main.py auth", "error")
        return
    elif args.force:
        authenticate(args.mode)
        kite = get_kite()
    else:
        kite = get_kite(mode=args.mode)

    profile = kite.profile()
    log(f"Logged in as {profile.get('user_name')} ({profile.get('user_id')})", "ok")
    margins = kite.margins()
    cash = margins.get("equity", {}).get("available", {}).get("cash")
    log(f"Available equity cash: {cash}", "info")


def cmd_coming_soon(name):
    def _run(args):
        print(f"🚧 The '{name}' module is not built yet. Stay tuned on the channel!")
    return _run


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Shubham Pareta AlgoTrading - simple Zerodha Kite toolkit",
    )
    sub = parser.add_subparsers(dest="command")

    # ---- auth ---------------------------------------------------------
    p = sub.add_parser("auth", help="login to Zerodha Kite and save the enctoken")
    p.add_argument("--mode", choices=["api_key", "auto", "manual"], help="override auth.mode from settings.json")
    p.add_argument("--check", action="store_true", help="only check if the saved session is still valid")
    p.add_argument("--force", action="store_true", help="ignore the saved session and login again")
    p.add_argument("--enctoken", metavar="TOKEN",
                   help="skip the login flow: save an enctoken you already copied from the browser")
    p.set_defaults(func=cmd_auth)

    # ---- data ---------------------------------------------------------
    from data.cli import register as register_data
    register_data(sub)

    # ---- placeholders for the next modules ----------------------------
    for name in ("backtest", "live"):
        q = sub.add_parser(name, help=f"{name} module (coming soon)")
        q.set_defaults(func=cmd_coming_soon(name))

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    try:
        args.func(args)
    except Exception as e:
        # KeyError/AttributeError & friends str() to almost nothing (just "'enctoken'"),
        # so show the exception type too.  ALGO_DEBUG=1 gives the full traceback.
        message = str(e) or repr(e)
        if isinstance(e, (KeyError, IndexError, AttributeError, TypeError, NameError)):
            message = f"{type(e).__name__}: {message}"
        print(f"\n❌ {message}\n")
        if os.environ.get("ALGO_DEBUG"):
            raise
        sys.exit(1)
