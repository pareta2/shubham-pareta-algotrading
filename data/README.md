# data module

Downloads candles from Zerodha and stores them as CSV files in `DataBank/`.
Re-running a fetch downloads **only the missing dates** (start, end or middle), never the whole range again.

```bash
python main.py data fetch --symbol RELIANCE --interval 5minute --days 30
python main.py data fetch --symbol NIFTY BANKNIFTY --interval day --from 2024-01-01 --to 2024-12-31
python main.py data search RELIANCE --exchange NFO      # find option / future symbols
python main.py data list                                # what do I already have?
python main.py data verify --symbol RELIANCE --interval 5minute --fix   # find & repair gaps
python main.py data ltp --symbol RELIANCE NIFTY         # live price check
```

Files:

| file | job |
|---|---|
| `instruments.py` | symbol name -> Zerodha instrument_token (downloads the public instrument list once a day) |
| `coverage.py` | date-range maths: what is already downloaded vs what is missing |
| `fetcher.py` | downloads only the missing ranges, in chunks, saving progress after each |
| `databank.py` | saves / merges / loads the CSV files and their `.meta.json` coverage records |
| `verify.py` | reports empty / partial days in a CSV; `--fix` re-downloads them once |
| `cli.py` | the `python main.py data ...` commands |

See the main README for details.
