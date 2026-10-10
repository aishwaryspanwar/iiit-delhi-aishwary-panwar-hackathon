import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.riskengine.config import DATA_DIR, load_yaml

RETURNS_PATH = DATA_DIR / "market" / "returns_daily.csv"


def main() -> None:
    market = load_yaml("ingestion.yaml")["market"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=market["history_start"])
    parser.add_argument("--end", default=market["history_end"])
    parser.add_argument("--out", type=Path, default=RETURNS_PATH)
    args = parser.parse_args()
    frame = yf.download(market["tickers"], start=args.start, end=args.end, auto_adjust=True, progress=False, threads=False)
    closes = frame["Close"][market["tickers"]].sort_index()
    returns = closes.pct_change(fill_method=None).iloc[1:]
    if "^TNX" in returns.columns:
        returns["^TNX"] = closes["^TNX"].diff().iloc[1:] * 100.0
        returns = returns.rename(columns={"^TNX": "^TNX_change_bp"})
    returns.index = pd.to_datetime(returns.index).strftime("%Y-%m-%d")
    returns.index.name = "date"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    returns.round(6).to_csv(args.out, lineterminator="\n", encoding="utf-8")
    missing = [c for c in returns.columns if returns[c].isna().all()]
    print(f"days={len(returns)} series={returns.shape[1]} missing={missing} -> {args.out}")


if __name__ == "__main__":
    main()
