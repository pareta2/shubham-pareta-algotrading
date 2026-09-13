# data module

Downloads candles from Zerodha and stores them as CSV files in `DataBank/`.

```bash
python main.py data fetch --symbol RELIANCE --interval 5minute --days 30
python main.py data fetch --symbol NIFTY BANKNIFTY --interval day --from 2024-01-01 --to 2024-12-31
python main.py data search RELIANCE --exchange NFO      # find option / future symbols
python main.py data list                                # what do I already have?
python main.py data ltp --symbol RELIANCE NIFTY         # live price check
```

Files:

| file | job |
|---|---|
| `instruments.py` | symbol name -> Zerodha instrument_token (downloads the public instrument list once a day) |
| `fetcher.py` | asks Kite for candles in chunks (Zerodha limits days per request) |
| `databank.py` | saves / merges / loads the CSV files |
| `cli.py` | the `python main.py data ...` commands |

See the main README for details.
