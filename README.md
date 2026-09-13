# Shubham Pareta AlgoTrading 🍒

A **simple, beginner-friendly** Python project for algo trading with Zerodha Kite.
Built step by step on the YouTube channel. No prior coding knowledge needed to
*use* it - and the code is written so you can *read* it too.

> ⚠️ This project logs in the same way your browser does (using the `enctoken`).
> It does not need a paid Kite Connect API key. Use it for personal / educational
> purposes only, and never share your `settings.json` or `enctoken.json`.

---

## 1. Project structure (the big picture)

```
shubham-pareta-algotrading/
│
├── main.py                 ← START HERE. One command-line "front door" for everything
├── requirements.txt        ← libraries to install
│
├── config/
│   ├── settings.example.json   ← template: copy to settings.json and fill in
│   ├── settings.json           ← YOUR secrets (git-ignored)
│   └── enctoken.json           ← auto-created after login (git-ignored)
│
├── common/                 ← tiny helpers shared by every module
│   ├── settings.py             ← reads settings.json
│   └── logger.py               ← pretty "[12:30:05] ✅ ..." messages
│
├── auth/                   ← MODULE 1: login to Zerodha  ✅ built
│   ├── kite_login.py           ← the 3 HTTP calls Zerodha needs (login → OTP → enctoken)
│   ├── gmail_otp.py            ← reads the OTP email from Gmail (AUTO mode)
│   ├── auto_auth.py            ← AUTO mode: no typing at all
│   ├── manual_auth.py          ← MANUAL mode: a small web page in your browser
│   ├── token_store.py          ← saves / loads enctoken.json
│   └── templates/              ← the HTML pages for MANUAL mode
│
├── broker/
│   └── kite_client.py          ← talks to Kite using the enctoken (profile, margins, ... more soon)
│
├── data/                   ← MODULE 2: download candles → CSV   🚧 next
│   └── DataBank/               ← CSV files land here
├── backtest/               ← MODULE 3: test strategies on CSVs  🚧 later
└── live/                   ← MODULE 4: trade live               🚧 later
```

**How the pieces talk to each other**

```
main.py  ──►  auth.get_kite()  ──►  is enctoken.json valid?
                                        │ yes → KiteClient  (done, no login needed)
                                        │ no  → auto_auth  or  manual_auth
                                        │          │              │
                                        │     Gmail / TOTP    browser page
                                        │          └──── kite_login.py ────┘
                                        │                      │
                                        └────── save enctoken.json ◄──────┘
```

---

## 2. Setup (one time)

### 2.1 Install Python
Python **3.9 or newer**. Check with:
```bash
python3 --version
```

### 2.2 Get the code and install libraries
```bash
cd shubham-pareta-algotrading
python3 -m venv venv              # optional but recommended: a private library folder
source venv/bin/activate          # Windows:  venv\Scripts\activate
pip install -r requirements.txt
```

### 2.3 Create your settings file
```bash
cp config/settings.example.json config/settings.json
```
Open `config/settings.json` in any text editor and fill it in:

| key | what to put |
|---|---|
| `zerodha.user_id` | your Kite login id, e.g. `AB1234` |
| `zerodha.password` | your Kite password |
| `zerodha.totp_secret` | only if you use TOTP (see 3.3) - else leave `""` |
| `gmail.email` | the Gmail address where Zerodha sends the OTP |
| `gmail.app_password` | a Gmail **App Password** (see 3.2) - NOT your normal password |
| `gmail.folder` | `Inbox` (change only if you auto-label Zerodha mails) |
| `auth.mode` | `auto` or `manual` |
| `auth.twofa_method` | `gmail_otp` or `totp` (AUTO mode only) |
| `auth.otp_wait_attempts` / `otp_wait_seconds` | how long AUTO mode waits for the email (10 × 10s = 100s) |
| `auth.manual_web_port` | port for the MANUAL login page (default `5055`) |

---

## 3. Authentication - step by step

Zerodha login always has **two** parts:

1. **User ID + Password**
2. **2FA** - a 6-digit code, which is either
   * an **OTP** that Zerodha sends to your SMS + email, **or**
   * a **TOTP** from an authenticator app (Google Authenticator, Authy, ...) if you turned that on in Kite.

This project supports both, in both modes.

### 3.1 MANUAL mode (easiest way to start)

```bash
python main.py auth --mode manual
```
* A web page opens at `http://127.0.0.1:5055`.
* Type your **User ID** and **Password**, pick **OTP** or **TOTP**, click *Continue*.
* Type the 6-digit code, click *Login*.
* The page says *Done* and the token is saved to `config/enctoken.json`.

Shortcut: if you are already logged in at kite.zerodha.com you can copy the
`enctoken` cookie from your browser (DevTools → Application → Cookies) and paste
it in the box at the bottom of the page.

### 3.2 AUTO mode with Gmail OTP (fully automatic)

Zerodha emails the OTP to your registered email. AUTO mode reads that email
for you. This works **only if TOTP is NOT enabled** on your Kite account
(when TOTP is on, Zerodha does not send OTP emails - use 3.3 instead).

**Gmail one-time setup**

1. Make sure your Zerodha registered email is this Gmail account.
2. Turn on **2-Step Verification** for the Google account:
   Google Account → Security → 2-Step Verification.
3. Create an **App Password**:
   Google Account → Security → *App passwords* → app name `algotrading` → *Create*.
   Google shows a 16-character password like `abcd efgh ijkl mnop`. Copy it into
   `gmail.app_password` (spaces are fine).
4. Enable IMAP: Gmail → ⚙ Settings → *See all settings* → *Forwarding and POP/IMAP*
   → **Enable IMAP** → Save.

Then in `settings.json` set `"auth": {"mode": "auto", "twofa_method": "gmail_otp"}` and run:
```bash
python main.py auth
```
What happens:
```
[09:01:10] ➡️  AUTO login for AB1234 using 2FA method 'gmail_otp'
[09:01:11] ✅ Password accepted ...
[09:01:11] ✅ Asked Zerodha to send the OTP (SMS + Email)
[09:01:11] ℹ️  Waiting 10s for the OTP email... (try 1/10)
[09:01:22] ✅ Found OTP email received at 2026-09-13 09:01:15
[09:01:22] ✅ OTP read from Gmail: 482913
[09:01:23] ✅ 2FA accepted - enctoken generated
[09:01:23] ✅ Token saved to config/enctoken.json
[09:01:24] ✅ Logged in as SHUBHAM PARETA (AB1234)
```

### 3.3 AUTO mode with TOTP (no email needed)

If you prefer authenticator-app style login:

1. Kite web → click your initials (top-right) → *My profile* → *Password & Security*
   → **Enable external 2FA TOTP**.
2. Zerodha shows a QR code **and a text secret** (something like `JBSWY3DPEHPK3PXP`).
   Scan the QR into your authenticator app **and** copy the text secret into
   `zerodha.totp_secret`.
3. Set `"twofa_method": "totp"` and run `python main.py auth`.

### 3.4 Using the login inside your own scripts

```python
from auth import get_kite

kite = get_kite()            # reuses the saved token, logs in only if needed
print(kite.profile())
print(kite.margins())
```

### 3.5 Handy commands

```bash
python main.py auth --check      # is the saved token still valid?
python main.py auth --force      # throw away the saved token and login again
python main.py auth --mode auto  # override the mode in settings.json for this run
```

---

## 4. Troubleshooting

| message | meaning / fix |
|---|---|
| `config/settings.json not found` | you skipped step 2.3 |
| `Login (step 1): Invalid username or password` | check `zerodha.user_id` / `password` |
| `Login (step 1): ... too many requests` | wait a few minutes, Zerodha rate-limits |
| `OTP email did not arrive` | TOTP is enabled on your account (use 3.3), IMAP off, wrong app password, or OTP email goes to a Gmail label ≠ Inbox |
| `imaplib.IMAP4.error: [AUTHENTICATIONFAILED]` | wrong `gmail.app_password` or 2-Step Verification not on |
| `2FA (step 3): Invalid TOTP` | wrong `totp_secret`, or your computer clock is off by > 30 s |
| `Token ... has EXPIRED` | normal every morning; just run `python main.py auth` again |

---

## 5. Roadmap

- [x] **auth** - auto (Gmail OTP / TOTP) and manual (browser page) login
- [ ] **data** - download candles by symbol / interval / duration into `data/DataBank/*.csv`
- [ ] **backtest** - run strategies on the CSVs
- [ ] **live** - run strategies on live ticks and place orders
