import argparse
import json
from pathlib import Path

import pandas as pd

from src.riskengine.config import DATA_DIR

EPISODE_RETURNS_PATH = DATA_DIR / "market" / "returns_episodes.csv"
CALIBRATION_PATH = DATA_DIR / "market" / "shock_calibration.json"
FULL_SEVERITY_MULTIPLE = 2.0
WINDOW_DAYS = 5
IG_SPREAD_DURATION = 8.5
HY_SPREAD_DURATION = 4.0
TICKERS = ["^GSPC", "^TNX", "^VIX", "LQD", "IEF", "HYG", "CL=F", "XLE", "XLF", "XLI", "XLY", "XLK", "XLB", "XLU"]
PRICE_TICKERS = [t for t in TICKERS if t not in ("^TNX", "^VIX")]
RATE_COLUMN = "^TNX_bp_from_start"
VOL_COLUMN = "^VIX_pts_from_start"
SECTOR_ETFS = {"energy": "XLE", "financials": "XLF", "industrials": "XLI", "consumer": "XLY", "technology": "XLK", "materials": "XLB", "utilities": "XLU"}
EPISODES = {
    "geopolitical": [
        {"name": "Crimea annexation", "start": "2014-02-18", "end": "2014-03-31", "select": "worst_equity"},
        {"name": "North Korea missile crisis", "start": "2017-08-01", "end": "2017-08-31", "select": "worst_equity"},
        {"name": "US strike on Soleimani", "start": "2019-12-26", "end": "2020-01-15", "select": "worst_equity"},
    ],
    "macroeconomic": [
        {"name": "Taper tantrum", "start": "2013-05-15", "end": "2013-07-10", "select": "largest_rate_rise"},
        {"name": "Q4 2018 Fed tightening sell-off", "start": "2018-10-01", "end": "2018-12-31", "select": "worst_equity"},
    ],
    "credit_event": [
        {"name": "US sovereign downgrade and euro-area credit stress", "start": "2011-07-20", "end": "2011-08-31", "select": "worst_equity"},
        {"name": "Energy high-yield stress", "start": "2015-12-01", "end": "2016-02-29", "select": "widest_hy"},
    ],
    "commodity_energy": [
        {"name": "Libya supply shock", "start": "2011-02-14", "end": "2011-03-15", "select": "largest_oil_rise"},
        {"name": "Abqaiq attack", "start": "2019-09-12", "end": "2019-09-30", "select": "largest_oil_rise"},
    ],
}


def download(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    frame = yf.download(TICKERS, start=start, end=end, auto_adjust=True, progress=False, threads=False)
    return frame["Close"][TICKERS].sort_index()


def derived_series(closes: pd.DataFrame) -> pd.DataFrame:
    closes = closes.dropna()
    derived = closes[PRICE_TICKERS].div(closes[PRICE_TICKERS].iloc[0])
    derived[RATE_COLUMN] = (closes["^TNX"] - closes["^TNX"].iloc[0]) * 100.0
    derived[VOL_COLUMN] = closes["^VIX"] - closes["^VIX"].iloc[0]
    return derived


def episode_returns() -> pd.DataFrame:
    frames = []
    for episodes in EPISODES.values():
        for episode in episodes:
            closes = download(episode["start"], (pd.Timestamp(episode["end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
            closes.index = pd.to_datetime(closes.index).strftime("%Y-%m-%d")
            derived = derived_series(closes)
            derived.insert(0, "episode", episode["name"])
            frames.append(derived)
    return pd.concat(frames)


def window_moves(levels: pd.DataFrame, end_index: int) -> dict:
    start_row, end_row = levels.iloc[end_index - WINDOW_DAYS], levels.iloc[end_index]
    ret = lambda t: float(end_row[t] / start_row[t] - 1.0)
    return {
        "from": levels.index[end_index - WINDOW_DAYS],
        "to": levels.index[end_index],
        "equity_market": ret("^GSPC"),
        "rates_bp": float(end_row[RATE_COLUMN] - start_row[RATE_COLUMN]),
        "ig_spread_bp": -(ret("LQD") - ret("IEF")) / IG_SPREAD_DURATION * 1e4,
        "hy_spread_bp": -(ret("HYG") - ret("IEF")) / HY_SPREAD_DURATION * 1e4,
        "vol_pts": float(end_row[VOL_COLUMN] - start_row[VOL_COLUMN]),
        "oil": ret("CL=F"),
        "sector_excess": {sector: ret(etf) - ret("^GSPC") for sector, etf in SECTOR_ETFS.items()},
    }


def select_window(levels: pd.DataFrame, rule: str) -> dict:
    candidates = [window_moves(levels, i) for i in range(WINDOW_DAYS, len(levels))]
    keys = {
        "worst_equity": lambda m: m["equity_market"],
        "largest_rate_rise": lambda m: -m["rates_bp"],
        "widest_hy": lambda m: -m["hy_spread_bp"],
        "largest_oil_rise": lambda m: -m["oil"],
    }
    return min(candidates, key=keys[rule])


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def calibrate(returns: pd.DataFrame) -> dict:
    result = {"method": {
        "window_trading_days": WINDOW_DAYS,
        "full_severity_multiple": FULL_SEVERITY_MULTIPLE,
        "ig_spread_proxy": f"-(LQD - IEF return) / {IG_SPREAD_DURATION}",
        "hy_spread_proxy": f"-(HYG - IEF return) / {HY_SPREAD_DURATION}",
        "rule": "base shock (severity multiplier 1.0, impact 10) = full_severity_multiple x mean of the analogue episodes' selected 5-day moves; at the trigger threshold (multiplier 0.5) the shock equals the analogue mean",
    }, "scenarios": {}}
    for scenario, episodes in EPISODES.items():
        windows = []
        for episode in episodes:
            levels = returns[returns["episode"] == episode["name"]].drop(columns=["episode"]).dropna()
            windows.append({"episode": episode["name"], "select": episode["select"], **select_window(levels, episode["select"])})
        mean = {key: average([w[key] for w in windows]) for key in ("equity_market", "rates_bp", "ig_spread_bp", "hy_spread_bp", "vol_pts")}
        mean["sector_excess"] = {s: average([w["sector_excess"][s] for w in windows]) for s in SECTOR_ETFS}
        base = {
            "equity_market": round(FULL_SEVERITY_MULTIPLE * mean["equity_market"], 3),
            "rates_bp": round(FULL_SEVERITY_MULTIPLE * mean["rates_bp"]),
            "spread_bp": {"IG": max(0, round(FULL_SEVERITY_MULTIPLE * mean["ig_spread_bp"])), "HY": max(0, round(FULL_SEVERITY_MULTIPLE * mean["hy_spread_bp"]))},
            "vol_pts": max(0.0, round(FULL_SEVERITY_MULTIPLE * mean["vol_pts"], 1)),
            "sector_excess": {s: round(FULL_SEVERITY_MULTIPLE * v, 3) for s, v in mean["sector_excess"].items()},
        }
        result["scenarios"][scenario] = {"episodes": windows, "analogue_mean": mean, "base_shock": base}
    return result


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download or not EPISODE_RETURNS_PATH.exists():
        derived = episode_returns()
        derived.index.name = "date"
        derived.round(6).to_csv(EPISODE_RETURNS_PATH, lineterminator="\n", encoding="utf-8")
    returns = pd.read_csv(EPISODE_RETURNS_PATH, index_col="date")
    calibration = rounded(calibrate(returns))
    Path(CALIBRATION_PATH).write_text(json.dumps(calibration, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v["base_shock"] for k, v in calibration["scenarios"].items()}, indent=1))


if __name__ == "__main__":
    main()
