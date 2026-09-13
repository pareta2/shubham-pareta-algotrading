"""
data  (package entry point)
---------------------------
What the other modules need from here:

    from data import load_candles
    df = load_candles("RELIANCE", "5minute")      # DataFrame from data/DataBank/NSE_RELIANCE_5minute.csv
"""

from data.databank import DATABANK_DIR, csv_path, list_databank, load_candles, save_candles  # noqa: F401
