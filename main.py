"""
main.py  -  the front door of the project
=========================================

Run everything from here.  Examples:

    python main.py auth                  # login using mode from settings.json
    python main.py auth --mode manual    # open the browser login page
    python main.py auth --mode auto      # fully automatic (Gmail OTP / TOTP)
    python main.py auth --check          # is my saved token still valid?
    python main.py auth --force          # ignore saved token, login again

Coming next:
    python main.py data ...              # download candles into data/DataBank
    python main.py backtest ...
    python main.py live ...
"""

import argparse
import sys


def cmd_auth(args):
    from auth import authenticate, get_kite
    from auth.token_store import load_token
    from broker.kite_client import KiteClient
    from common.logger import log

    if args.check:
        saved = load_token()
        if not saved:
            log("No saved token. Run:  python main.py auth", "warn")
            return
        if KiteClient(saved["enctoken"]).is_token_valid():
            log(f"Token from {saved['generated_at']} is VALID ✔", "ok")
        else:
            log(f"Token from {saved['generated_at']} has EXPIRED. Run:  python main.py auth", "error")
        return

    if args.force:
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
    p.add_argument("--mode", choices=["auto", "manual"], help="override auth.mode from settings.json")
    p.add_argument("--check", action="store_true", help="only check if the saved token is still valid")
    p.add_argument("--force", action="store_true", help="ignore the saved token and login again")
    p.set_defaults(func=cmd_auth)

    # ---- placeholders for the next modules ----------------------------
    for name in ("data", "backtest", "live"):
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
        print(f"\n❌ {e}\n")
        sys.exit(1)
