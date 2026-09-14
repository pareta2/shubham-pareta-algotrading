"""
auth/api_key_auth.py
--------------------
The OFFICIAL Zerodha login - Kite Connect (https://kite.trade).
This is the method recommended by Zerodha and the one shown on the channel.

How it works (3 steps):

    1. We open  https://kite.zerodha.com/connect/login?v=3&api_key=YOUR_KEY
       in your browser.  YOU log in there with user id, password and 2FA.
    2. Zerodha sends the browser to your app's "Redirect URL" with
       ?request_token=XXXX in the address bar.
         - If your Redirect URL is  http://127.0.0.1:5055/  this program catches
           it automatically (a tiny local web server is listening).
         - Otherwise, copy the request_token from the address bar and paste it
           in the terminal.
    3. We swap the request_token for an access_token by calling
       POST https://api.kite.trade/session/token  with
       checksum = sha256(api_key + request_token + api_secret)

The access_token works until early next morning.
"""

import hashlib
import threading
import webbrowser

import requests
from flask import Flask, render_template, request
from werkzeug.serving import make_server

from common.logger import log
from common.settings import get

LOGIN_URL = "https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
TOKEN_URL = "https://api.kite.trade/session/token"


def exchange_request_token(api_key: str, api_secret: str, request_token: str) -> dict:
    """Step 3: request_token -> access_token (+ user details)."""
    checksum = hashlib.sha256((api_key + request_token + api_secret).encode("utf-8")).hexdigest()
    response = requests.post(
        TOKEN_URL,
        headers={"X-Kite-Version": "3"},
        data={"api_key": api_key, "request_token": request_token, "checksum": checksum},
        timeout=15,
    )
    body = response.json()
    if response.status_code != 200 or body.get("status") != "success":
        raise Exception(f"Token exchange failed: {body.get('message', body)}")
    return body["data"]


def api_key_login(settings: dict) -> dict:
    """Run the full login.  Returns a session dict for config/session.json."""
    api_key = get(settings, "kite_api", "api_key")
    api_secret = get(settings, "kite_api", "api_secret")
    port = get(settings, "auth", "local_web_port", default=5055)
    if not api_key or not api_secret:
        raise ValueError("kite_api.api_key / kite_api.api_secret missing in config/settings.json "
                         "(see README -> 'Get your Kite Connect API key')")

    state = {"request_token": None}
    got_token = threading.Event()

    # ---- way 1: local web server catches the redirect ----------------
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_redirect(path):
        token = request.args.get("request_token")
        if token and not got_token.is_set():
            state["request_token"] = token
            got_token.set()
            return render_template("api_key_done.html")
        return render_template("api_key_waiting.html", status=request.args.get("status"))

    server = make_server("127.0.0.1", port, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # ---- way 2: user pastes the request_token in the terminal ----------
    def read_from_terminal():
        try:
            typed = input().strip()
        except EOFError:
            return
        if typed and not got_token.is_set():
            # accept a full redirect URL or just the token
            if "request_token=" in typed:
                typed = typed.split("request_token=")[1].split("&")[0]
            state["request_token"] = typed
            got_token.set()

    threading.Thread(target=read_from_terminal, daemon=True).start()

    # ---- open the browser and wait for either way --------------------
    url = LOGIN_URL.format(api_key=api_key)
    log("Opening Zerodha login in your browser (log in with your user id, password and 2FA)", "step")
    log(f"  {url}")
    log(f"If your app's Redirect URL is http://127.0.0.1:{port}/ the token is caught automatically.", "info")
    log("Otherwise paste the request_token (or the whole redirected URL) here and press Enter:", "info")
    webbrowser.open(url)

    got_token.wait()
    server.shutdown()

    log("request_token received - exchanging it for an access_token", "ok")
    data = exchange_request_token(api_key, api_secret, state["request_token"])
    log(f"Logged in as {data.get('user_name')} ({data.get('user_id')})", "ok")
    return {
        "auth_type": "api_key",
        "api_key": api_key,
        "access_token": data["access_token"],
        "user_id": data.get("user_id", ""),
        "user_name": data.get("user_name", ""),
    }
