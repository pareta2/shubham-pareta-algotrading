# Command Cheat Sheet

Every command in this project runs through `main.py`.

```bash
python3 main.py <module> <action> [flags]
```

Modules: `auth`, `data`, `backtest` (coming soon), `live` (coming soon).

---

## Auth

```bash
python3 main.py auth                   # login using auth.mode from config/settings.json
python3 main.py auth --mode api_key    # official Kite Connect (recommended)
python3 main.py auth --mode manual     # enctoken via browser page (unofficial)
python3 main.py auth --mode auto       # enctoken, fully automatic (unofficial)
python3 main.py auth --check           # is my saved session still valid?
python3 main.py auth --force           # ignore saved session, login again
```

The session is cached in `config/session.json`, so you normally log in once a day.

---

## Data - fetch candles

```bash
python3 main.py data fetch --symbol RELIANCE --interval 5minute --days 30
python3 main.py data fetch --symbol NIFTY BANKNIFTY --interval day --from 2024-01-01 --to 2024-12-31
python3 main.py data fetch --symbol NIFTY25OCT25000CE --exchange NFO --interval 5m --days 10 --oi
python3 main.py data fetch --symbol RELIANCE --interval 5minute --days 30 --force
```

| flag | default | meaning |
|---|---|---|
| `--symbol` | *required* | one or many, space-separated |
| `--exchange` | `NSE` | `NSE` `BSE` `NFO` `BFO` `MCX` `CDS` |
| `--interval` | `5minute` | see the interval table below |
| `--days` | `30` | days back from today |
| `--from` | - | `YYYY-MM-DD`, overrides `--days` |
| `--to` | today | `YYYY-MM-DD` |
| `--oi` | off | also fetch open interest (F&O only) |
| `--force` | off | re-download everything, ignoring existing coverage |

Re-running a fetch downloads **only the missing dates** - the `.meta.json` file next to
each CSV records which ranges are already on disk.

---

## Data - search instruments

```bash
python3 main.py data search RELIANCE                             # first 30 matches only
python3 main.py data search nifty --limit 999999 | less           # ALL matches (~6,200)
python3 main.py data search nifty --exchange NFO --limit 999999   # one exchange
python3 main.py data search NIFTY25OCT --exchange NFO --limit 500
```

| flag | default | meaning |
|---|---|---|
| `text` | *required* | positional; substring of `tradingsymbol` **or** `name` |
| `--exchange` | all | limit to one exchange |
| `--limit` | `30` | max rows printed - raise it to see everything |

The instrument list (`data/DataBank/instruments.csv`) is Zerodha's public CSV and
refreshes automatically once a day. No login needed for `search`.

---

## Data - verify / repair a CSV

```bash
python3 main.py data verify --symbol RELIANCE --interval 5minute
python3 main.py data verify --symbol RELIANCE --interval 5minute --fix
```

Reports empty and partial trading days. `--fix` re-downloads the suspicious days once.
`--exchange` and `--interval` default the same way as `fetch`.

---

## Data - list & live price

```bash
python3 main.py data list                          # what is already in the DataBank
python3 main.py data ltp --symbol RELIANCE NIFTY   # last traded price (login smoke test)
python3 main.py data ltp --symbol GOLD --exchange MCX
```

---

## Intervals

Canonical name, the aliases you can type instead, and Zerodha's cap per request:

| interval | aliases | max days / request |
|---|---|---|
| `minute` | `1m` `1min` `1minute` | 60 |
| `3minute` | `3m` | 100 |
| `5minute` | `5m` | 100 |
| `10minute` | `10m` | 100 |
| `15minute` | `15m` | 200 |
| `30minute` | `30m` | 200 |
| `60minute` | `1h` `60m` `hour` | 400 |
| `day` | `1d` `d` `daily` | 2000 |

Splitting a long request across the cap is automatic - asking for 5 years of
`5minute` candles just means more chunks, and progress is saved after each one.

---

## Index nicknames

Work in `fetch`, `verify` and `ltp` (not in `search`, which matches raw text):

| you type | Zerodha name |
|---|---|
| `NIFTY` / `NIFTY50` | NSE : NIFTY 50 |
| `BANKNIFTY` | NSE : NIFTY BANK |
| `FINNIFTY` | NSE : NIFTY FIN SERVICE |
| `MIDCPNIFTY` | NSE : NIFTY MID SELECT |
| `SENSEX` | BSE : SENSEX |
| `BANKEX` | BSE : BANKEX |
| `INDIAVIX` | NSE : INDIA VIX |

---

## Where things live

| path | what it is |
|---|---|
| `data/DataBank/<EXCHANGE>_<SYMBOL>_<interval>.csv` | the candles |
| `data/DataBank/<...>.meta.json` | which dates are already downloaded |
| `data/DataBank/instruments.csv` | Zerodha's full instrument list (daily refresh) |
| `config/settings.json` | your API key / credentials (gitignored) |
| `config/session.json` | saved login token (gitignored) |

---

## Gotchas

- Everything except `auth --check` and `data search` / `data list` needs a live login -
  run `python3 main.py auth` first.
- Today's candles only count as complete after **16:00**; before that, today is
  re-fetched on the next run.
- `--oi` is F&O only - it will error on NSE equity.
- `data search` prints only 30 rows by default. Raise `--limit` if a symbol seems missing.
- `python3 main.py data` with no action prints the data help.
