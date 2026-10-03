import json
from pathlib import Path

import pandas as pd
import yfinance as yf

TWEET_TICKERS = [
    "TSLA", "MSFT", "PG", "META", "AMZN", "GOOG", "AMD", "AAPL", "NFLX", "TSM", "KO", "F", "COST",
    "DIS", "VZ", "CRM", "INTC", "BA", "BX", "NOC", "PYPL", "ENPH", "NIO", "ZS", "XPEV",
]
MARKET_TICKERS = ["^GSPC", "^VIX", "^TNX", "XLE", "XLF", "XLK", "XLI", "XLU", "XLY", "XLP", "XLB", "HYG", "LQD", "IEF"]
WINDOWS = {"W1": ("2022-02-10", "2022-03-24"), "W2": ("2022-04-25", "2022-05-25"), "W3": ("2022-09-10", "2022-09-30")}
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "spike_prices.json"


def max_gap_business_days(index: pd.DatetimeIndex) -> int:
    if len(index) < 2:
        return 9999
    gaps = [len(pd.bdate_range(a, b)) - 2 for a, b in zip(index[:-1], index[1:])]
    return max(gaps)


def main() -> None:
    tickers = TWEET_TICKERS + MARKET_TICKERS
    frame = yf.download(tickers, start="2022-01-01", end="2022-11-01", auto_adjust=True, progress=False, threads=True)
    closes = frame["Close"]
    report = {}
    for label, (start, end) in WINDOWS.items():
        window = closes.loc[start:end]
        per_ticker = {}
        for ticker in tickers:
            series = window[ticker].dropna() if ticker in window else pd.Series(dtype=float)
            per_ticker[ticker] = {"rows": int(series.shape[0]), "max_gap_bdays": max_gap_business_days(series.index)}
        failing = [t for t, v in per_ticker.items() if v["rows"] == 0 or v["max_gap_bdays"] > 2]
        report[label] = {"trading_days": int(window.shape[0]), "failing": failing, "per_ticker": per_ticker}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for label, data in report.items():
        print(label, "trading_days", data["trading_days"], "failing", data["failing"])


if __name__ == "__main__":
    main()
