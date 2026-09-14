# Shubham Pareta AlgoTrading 🍒

A **simple, beginner-friendly** Python project for algo trading with Zerodha Kite.
Built module by module for my YouTube channel. No prior coding knowledge needed to
*use* it - and the code is commented so you can *read* it whenever you are curious.

> ▶️ **Watch the videos & subscribe for the latest updates:**
> **https://www.youtube.com/@shubhampareta**
> The videos show you **how to set up and use each module with a live demo** - this README
> is the written companion with all the steps and commands. For the details of how the
> code works, read the comments inside each file.

> ⚠️ **Important note on login methods** - please read
>
> The **recommended and only officially supported way** to connect a program to Zerodha is the
> **Kite Connect API** (API key + secret from https://kite.trade). That is what I use and what
> I show in the videos.
>
> This repo *also* contains two **unofficial** login methods (`auto` and `manual`) that reuse
> the browser's `enctoken`. Zerodha and SEBI do not endorse this kind of login. I, Shubham Pareta,
> **do not promote or recommend** those methods. They are kept only for learners who cannot afford
> an API subscription and want to experiment for **educational purposes**. If you use them, you do
> so entirely at your own risk - I take **no responsibility** for account restrictions, data
> issues, or losses arising from them. Please use the API key method for anything real.
>
> Never share your `config/settings.json` or `config/session.json` with anyone.

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
│   └── session.json            ← auto-created after login (git-ignored)
│
├── common/                 ← tiny helpers shared by every module
│   ├── settings.py             ← reads settings.json
│   └── logger.py               ← pretty "[12:30:05] ✅ ..." messages
│
├── auth/                   ← MODULE 1: login to Zerodha  ✅ built
│   ├── api_key_auth.py         ← API_KEY mode: official Kite Connect login  ★ recommended
│   ├── kite_login.py           ← (unofficial) the 3 HTTP calls behind the enctoken login
│   ├── gmail_otp.py            ← (unofficial) reads the OTP email from Gmail (AUTO mode)
│   ├── auto_auth.py            ← (unofficial) AUTO mode: no typing at all
│   ├── manual_auth.py          ← (unofficial) MANUAL mode: a small web page in your browser
│   ├── token_store.py          ← saves / loads session.json
│   └── templates/              ← the HTML pages used by the browser flows
│
├── broker/
│   └── kite_client.py          ← ONE client for both api.kite.trade (API key) and kite.zerodha.com (enctoken)
│
├── data/                   ← MODULE 2: download candles → CSV   ✅ built
│   ├── instruments.py          ← symbol name → instrument_token (public list, cached daily)
│   ├── coverage.py             ← date-range maths: "which part of what you asked is still missing?"
│   ├── fetcher.py              ← downloads ONLY the missing candles, chunk by chunk, resumable
│   ├── databank.py             ← saves / merges / loads the CSV files + their .meta.json
│   ├── verify.py               ← health-check a CSV for missing / partial days, repair with --fix
│   ├── cli.py                  ← the  python main.py data ...  commands
│   └── DataBank/               ← CSV files land here (one per symbol + interval)
├── backtest/               ← MODULE 3: test strategies on CSVs  🚧 later
└── live/                   ← MODULE 4: trade live               🚧 later
```

**How the pieces talk to each other**

```
main.py  ──►  auth.get_kite()  ──►  is session.json still valid?
                                        │ yes → KiteClient  (done, no login needed)
                                        │ no  → login with auth.mode from settings.json
                                        │        ┌──────────────┼──────────────┐
                                        │    api_key          auto           manual
                                        │  (official,      (enctoken,      (enctoken,
                                        │   browser +       Gmail/TOTP)     browser page)
                                        │   request_token)      └── kite_login.py ──┘
                                        │        │                      │
                                        └──── save session.json ◄───────┘
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
| `auth.mode` | `api_key` (recommended), or the unofficial `auto` / `manual` |
| `auth.local_web_port` | port for the local login page / redirect catcher (default `5055`) |
| `kite_api.api_key` | from your Kite Connect app (see 3.1) |
| `kite_api.api_secret` | from your Kite Connect app (see 3.1) |
| `zerodha.user_id` | your Kite login id, e.g. `AB1234` |
| `zerodha.password` | **only** for the unofficial `auto` / `manual` modes - else leave `""` |
| `zerodha.totp_secret` | **only** for unofficial `auto` mode with TOTP (see 3.4) |
| `gmail.*` | **only** for unofficial `auto` mode with Gmail OTP (see 3.3) |
| `auth.twofa_method` | `gmail_otp` or `totp` (unofficial `auto` mode only) |
| `auth.otp_wait_attempts` / `otp_wait_seconds` | how long `auto` mode waits for the email (10 × 10s = 100s) |

---

## 3. Authentication - step by step

### 3.1 ★ Recommended: Kite Connect API key (official)

This is the method Zerodha supports and the one I show in the videos.
You log in **yourself** in the browser (user id, password, 2FA) - the program never
sees your password. Zerodha then gives the program a token that works for the day.

**Get your API key (one time, ~5 minutes)**

1. Go to the Kite Connect developer portal: **https://developers.kite.trade/signup**
   and sign up (use the email linked to your Zerodha account).
2. Pick a plan on **https://developers.kite.trade/**:

   | plan | price | what you get |
   |---|---|---|
   | **Personal** | free | orders, GTT, positions, holdings, funds - **no** historical / live market data |
   | **Connect** | ₹500 / month per API key | everything + **historical candles** + live WebSocket data |

   For the **Data** and **Backtest** modules you need historical candles, i.e. the ₹500 plan.
   The free Personal plan is enough to try the **Auth** module and later place orders.
   (Prices as of Sept 2026 - check the portal for the latest. Official pricing page:
   https://zerodha.com/products/api/)
3. Click **My Apps → Create new app** and fill in:

   | field | value |
   |---|---|
   | App name | anything, e.g. `ShubhamAlgo` |
   | Zerodha Client ID | your Kite user id, e.g. `AB1234` |
   | **Redirect URL** | `http://127.0.0.1:5055/` ← use exactly this so the program can catch the login automatically |
   | Postback URL | leave blank |
   | Description | anything |

4. Open the app you just created and copy the **API key** and **API secret** into
   `config/settings.json` under `kite_api`. Set `"auth": {"mode": "api_key"}`.

   Zerodha's own step-by-step article:
   https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect
   Kite Connect API documentation: https://kite.trade/docs/connect/v3/

**Log in (once per trading day)**

```bash
python main.py auth
```
What happens:

1. Your browser opens `https://kite.zerodha.com/connect/login?v=3&api_key=...`.
2. You log in on Zerodha's own page with user id, password and OTP/TOTP.
3. Zerodha redirects to `http://127.0.0.1:5055/?request_token=...`. The program is
   listening there, grabs the `request_token` and shows a *Done* page.
   *(If you registered a different Redirect URL, just copy the `request_token` from the
   address bar - or the whole URL - and paste it into the terminal.)*
4. The program exchanges the `request_token` for an `access_token`
   (`POST https://api.kite.trade/session/token` with a SHA-256 checksum of
   `api_key + request_token + api_secret`) and saves it to `config/session.json`.

```
[09:01:10] ➡️  Opening Zerodha login in your browser (log in with your user id, password and 2FA)
[09:01:31] ✅ request_token received - exchanging it for an access_token
[09:01:32] ✅ Logged in as SHUBHAM PARETA (AB1234)
[09:01:32] ✅ Session saved to config/session.json
[09:01:33] ✅ Logged in as SHUBHAM PARETA (AB1234)
[09:01:33] ℹ️  Available equity cash: 12345.0
```

All later calls go to `https://api.kite.trade` with the header
`Authorization: token api_key:access_token` - exactly as documented by Zerodha.

> 📌 **Planning to place orders through the API (the Live module)?** Two things to arrange
> in advance, per SEBI/NSE rules effective April 2026:
> * **Static IP** - order placement is accepted only from a static IP registered on your Kite
>   Connect developer profile (data, positions, order book etc. work from any IP). Most home
>   broadband gives a changing IP, so ask your ISP for a static one or use a small cloud VM.
>   How to add it: https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip
> * **Market protection** - MARKET and SL-M orders must carry a market-protection value
>   (orders sent with `0` are rejected). The Live module will set this for you.
>
> Data and Backtest need neither - only Live does.

---

### 3.2 – 3.4 Unofficial enctoken methods (not recommended)

> ⚠️ **Read the note at the top of this README first.** These methods log in the way a
> browser does and reuse the `enctoken` cookie. They are **not endorsed by Zerodha or SEBI**,
> I do not promote them, and I take no responsibility for their use. They exist only so that
> learners without an API subscription can follow the educational content.

With these methods the program handles both parts of the Zerodha login:

1. **User ID + Password**
2. **2FA** - a 6-digit code, either an **OTP** that Zerodha sends to SMS + email, or a
   **TOTP** from an authenticator app if you turned that on in Kite.

Calls then go to `https://kite.zerodha.com/oms` with `Authorization: enctoken ...`.
Same endpoint paths as the official API, different base URL - `broker/kite_client.py`
picks the right one automatically.

### 3.2 MANUAL mode (unofficial)

```bash
python main.py auth --mode manual
```
* A web page opens at `http://127.0.0.1:5055`.
* Type your **User ID** and **Password**, pick **OTP** or **TOTP**, click *Continue*.
* Type the 6-digit code, click *Login*.
* The page says *Done* and the token is saved to `config/session.json`.

Shortcut: if you are already logged in at kite.zerodha.com you can copy the
`enctoken` cookie from your browser (DevTools → Application → Cookies) and paste
it in the box at the bottom of the page.

### 3.3 AUTO mode with Gmail OTP (unofficial, fully automatic)

Zerodha emails the OTP to your registered email. AUTO mode reads that email
for you. This works **only if TOTP is NOT enabled** on your Kite account
(when TOTP is on, Zerodha does not send OTP emails - use 3.4 instead).

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
[09:01:23] ✅ Session saved to config/session.json
[09:01:24] ✅ Logged in as SHUBHAM PARETA (AB1234)
```

### 3.4 AUTO mode with TOTP (unofficial, no email needed)

If you prefer authenticator-app style login:

1. Kite web → click your initials (top-right) → *My profile* → *Password & Security*
   → **Enable external 2FA TOTP**.
2. Zerodha shows a QR code **and a text secret** (something like `JBSWY3DPEHPK3PXP`).
   Scan the QR into your authenticator app **and** copy the text secret into
   `zerodha.totp_secret`.
3. Set `"twofa_method": "totp"` and run `python main.py auth`.

### 3.5 Using the login inside your own scripts

```python
from auth import get_kite

kite = get_kite()            # reuses the saved session, logs in only if needed
print(kite.profile())        # works the same whichever login mode you used
print(kite.margins())
```

### 3.6 Handy commands

```bash
python main.py auth --check         # is the saved session still valid?
python main.py auth --force         # throw away the saved session and login again
python main.py auth --mode api_key  # override the mode in settings.json for this run
```

---

## 4. Data module - download candles to CSV

Every command needs a valid login; `get_kite()` handles that for you
(it reuses the saved token or logs in using your `auth.mode`).

### 4.1 Fetch candles

```bash
# last 30 days of 5-minute candles for Reliance  ->  data/DataBank/NSE_RELIANCE_5minute.csv
python main.py data fetch --symbol RELIANCE --interval 5minute --days 30

# several symbols at once, daily candles, exact date range
python main.py data fetch --symbol NIFTY BANKNIFTY RELIANCE --interval day --from 2024-01-01 --to 2024-12-31

# an option contract with open interest (exchange NFO)
python main.py data fetch --symbol NIFTY26SEP24500CE --exchange NFO --interval 5minute --days 10 --oi
```

> ⚠️ **Expired contracts cannot be downloaded.** Zerodha serves historical candles only for
> instruments that are still in today's instrument list. Once an option or future expires it
> disappears from the list, and its history goes with it. If you want option data for
> backtesting, fetch it **while the contract is live** and keep the CSV - the DataBank never
> deletes anything. Indices and stocks are not affected.

| option | meaning |
|---|---|
| `--symbol` | one or more trading symbols. Index nicknames work: `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`, `SENSEX`, `BANKEX`, `INDIAVIX` |
| `--exchange` | `NSE` (default), `BSE`, `NFO`, `BFO`, `MCX`, `CDS` |
| `--interval` | `minute` `3minute` `5minute` `10minute` `15minute` `30minute` `60minute` `day` - short forms `1m 5m 15m 1h 1d` also work |
| `--days` | how many days back from today (default 30) |
| `--from` / `--to` | exact dates `YYYY-MM-DD` (`--from` overrides `--days`) |
| `--oi` | also store open interest (futures & options only) |

CSV columns: `date, open, high, low, close, volume [, oi]` - `date` is plain IST time
like `2024-02-01 09:15:00`.

### 4.2 Smart re-fetch: only the missing part is downloaded

Next to every CSV sits a tiny `*.meta.json` that remembers which **date ranges are
already downloaded**. Every fetch first subtracts those from what you asked for and
downloads only the gaps - at the start, at the end, or in the middle.

```
yesterday : data fetch --symbol NIFTY --interval 5minute --from 2016-01-01     (10 years, ~40 calls)
today     : data fetch --symbol NIFTY --interval 5minute --from 2016-01-01     (only today: 1 call)

[09:05:01] ℹ️  NIFTY 50 5minute: already have [2016-01-01..2026-09-12]
[09:05:01] ➡️  NIFTY 50 5minute: downloading only [2026-09-13..2026-09-13]
```

Other things this gives you for free:

* **Resume after a crash** - progress is written to disk after every chunk, so if your
  internet drops halfway through a big download, just run the same command again and it
  continues from the missing chunk.
* **Today is special** - candles for today are fetched, but the day is only marked as
  "complete" after 16:00 IST. Fetch again tomorrow and today's full session is refreshed.
* **Escape hatch** - `--force` ignores the meta file and downloads the whole range again.

### 4.3 Verify (and repair) a CSV

```bash
python main.py data verify --symbol NIFTY --interval 5minute
python main.py data verify --symbol NIFTY --interval 5minute --fix
```
```
📋 NIFTY 50 5minute
   candles   : 1,84,230
   covered   : 2016-01-01..2026-09-12
   usual day : 75 candles
   empty weekdays  : 14  (e.g. 2024-01-26, 2024-03-08, ...)
   partial days    : 1   (e.g. 2024-06-04=41 ...)
   ➜ run again with --fix to re-download these days once
```
* **empty weekdays** = Mon-Fri inside a covered range with no candles. Usually holidays.
* **partial days** = far fewer candles than a normal day (below 80 % of the usual count).
  Could be a half-day session, or a download that got cut off.

`--fix` re-downloads those days **once** and notes them in the meta file, so a real
holiday or a half-day session is never downloaded again and again.

### 4.4 Find symbols

```bash
python main.py data search RELIANCE                    # anywhere
python main.py data search NIFTY26SEP --exchange NFO   # this month's Nifty F&O contracts
```
The instrument list (about 1.1 lakh rows) is downloaded once a day from Zerodha's
public URL into `data/DataBank/instruments.csv`.

### 4.5 See what you have / quick price check

```bash
python main.py data list                       # each CSV: rows, date range, covered ranges
python main.py data ltp --symbol RELIANCE NIFTY
```

### 4.6 Use the data in your own script

```python
from data import load_candles

df = load_candles("RELIANCE", "5minute")       # pandas DataFrame, or None if not fetched yet
print(df.tail())
```

Zerodha keeps intraday history for roughly the last few years and daily history
for much longer. Requests are made in chunks (e.g. 60 days of 1-minute candles per
call) with a short pause between them, so a big download can take a minute or two.

---

## 5. Troubleshooting

| message | meaning / fix |
|---|---|
| `config/settings.json not found` | you skipped step 2.3 |
| `kite_api.api_key / api_secret missing` | fill them in from https://developers.kite.trade (see 3.1) |
| `Token exchange failed: Invalid checksum` / `Token is invalid or has expired` | wrong `api_secret`, or you pasted an old `request_token` (each one works once, for a few minutes) - run `python main.py auth` again |
| browser shows Zerodha error `Invalid api_key` | wrong `kite_api.api_key` |
| after login the browser lands on a page that is not `127.0.0.1:5055` | your app's Redirect URL is different - copy `request_token` from the address bar and paste it in the terminal, or change the Redirect URL in the developer portal |
| `Kite API error 403: Insufficient permission for that call` | you are on the free Personal plan - historical / live data needs the ₹500 Connect plan |
| `Login (step 1): Invalid username or password` | check `zerodha.user_id` / `password` |
| `Login (step 1): ... too many requests` | wait a few minutes, Zerodha rate-limits |
| `OTP email did not arrive` | TOTP is enabled on your account (use 3.4), IMAP off, wrong app password, or OTP email goes to a Gmail label ≠ Inbox |
| `imaplib.IMAP4.error: [AUTHENTICATIONFAILED]` | wrong `gmail.app_password` or 2-Step Verification not on |
| `2FA (step 3): Invalid TOTP` | wrong `totp_secret`, or your computer clock is off by > 30 s |
| `Session ... has EXPIRED` | normal every morning; just run `python main.py auth` again |
| `'XYZ' not found on NSE` | wrong spelling or wrong exchange - use `python main.py data search XYZ` |
| `Kite API error 400: ... interval` / `... from date` | date range too old for that interval, or invalid interval name |
| `Kite API error 429` | too many requests - wait a minute and retry (the fetcher already pauses between chunks) |

---

## 6. Roadmap

- [x] **auth** - official Kite Connect API key login (+ unofficial auto / manual enctoken modes)
- [x] **data** - download candles by symbol / interval / duration into `data/DataBank/*.csv`
- [ ] **backtest** - run strategies on the CSVs
- [ ] **live** - run strategies on live ticks and place orders
