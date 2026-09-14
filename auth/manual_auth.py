"""
auth/manual_auth.py
-------------------
MANUAL mode = a small web page opens in your browser (http://localhost:PORT).

    Page 1: enter User ID + Password, choose OTP or TOTP        -> POST /login
    Page 2: enter the 6-digit code                              -> POST /twofa
    Page 3: "Done!"  -> the server stops itself and returns the enctoken

There is also a shortcut box on Page 1: if you already copied an enctoken
from your browser (kite.zerodha.com -> DevTools -> Cookies), paste it there.

Built with Flask because its code reads almost like plain English.
"""

import logging
import threading
import webbrowser

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.serving import make_server

from auth.kite_login import TWOFA_OTP, TWOFA_TOTP, KiteLoginError, KiteLoginSession
from common.logger import log
from common.settings import get


def manual_login(settings: dict) -> str:
    port = get(settings, "auth", "local_web_port", default=5055)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)   # hide noisy request logs
    app = Flask(__name__)                 # Flask finds ./templates automatically
    app.config["SECRET_KEY"] = "local-only"

    # shared "memory" between the web pages and this function
    state = {"kite": None, "enctoken": None, "twofa_type": None}
    finished = threading.Event()

    # ---------------------------------------------------------------- pages
    @app.route("/")
    def page_login():
        return render_template(
            "login.html",
            user_id=get(settings, "zerodha", "user_id", default=""),
            error=request.args.get("error"),
        )

    @app.route("/login", methods=["POST"])
    def do_login():
        # shortcut: user pasted an enctoken directly
        pasted = request.form.get("enctoken", "").strip()
        if pasted:
            state["enctoken"] = pasted
            return redirect(url_for("page_done"))

        user_id = request.form.get("user_id", "").strip().upper()
        password = request.form.get("password", "")
        method = request.form.get("method", "otp")
        try:
            kite = KiteLoginSession()
            kite.login(user_id, password)
            if method == "otp":
                kite.request_otp()
                state["twofa_type"] = TWOFA_OTP
            else:
                state["twofa_type"] = TWOFA_TOTP
            state["kite"] = kite
            log(f"Password accepted for {user_id}; waiting for 2FA code in browser", "ok")
            return redirect(url_for("page_twofa"))
        except KiteLoginError as e:
            log(str(e), "error")
            return redirect(url_for("page_login", error=str(e)))

    @app.route("/twofa")
    def page_twofa():
        if state["kite"] is None:
            return redirect(url_for("page_login"))
        return render_template(
            "twofa.html",
            method=state["twofa_type"],
            user_id=state["kite"].user_id,
            error=request.args.get("error"),
        )

    @app.route("/twofa", methods=["POST"])
    def do_twofa():
        code = request.form.get("code", "")
        try:
            state["enctoken"] = state["kite"].submit_twofa(code, state["twofa_type"])
            return redirect(url_for("page_done"))
        except KiteLoginError as e:
            log(str(e), "error")
            return redirect(url_for("page_twofa", error=str(e)))

    @app.route("/done")
    def page_done():
        finished.set()                    # tells manual_login() we are finished
        return render_template("done.html", enctoken=state["enctoken"])

    # -------------------------------------------------------------- server
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    log(f"MANUAL login page: {url}   (opening in your browser...)", "step")
    webbrowser.open(url)

    finished.wait()                       # block here until /done is shown
    server.shutdown()
    thread.join(timeout=3)

    log("Login finished - enctoken received from the browser page", "ok")
    return state["enctoken"]
