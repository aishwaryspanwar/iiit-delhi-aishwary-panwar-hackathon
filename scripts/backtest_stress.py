import argparse
import json
from pathlib import Path

from scripts.evaluate import COMPARISON_WINDOWS, available_windows, read_rows, trading_day_for
from src.riskengine.config import DATA_DIR, PROCESSED_DIR
from src.riskengine.io import read_json
from src.stress.portfolio_gen import load_portfolio

BACKTEST_PATH = DATA_DIR / "eval" / "backtest.json"
HORIZONS = [1, 5]
BOND_PROXIES = {("corporate", "IG"): "LQD", ("corporate", "HY"): "HYG", ("sovereign_us", "IG"): "IEF"}
HY_RATINGS = {"BB+", "BB", "BB-", "B+", "B", "B-", "CCC"}


def proxy_for(position: dict) -> str | None:
    if position["asset_class"] == "equity":
        return position["ticker"]
    if position["asset_class"] != "bond":
        return None
    if position["sector"] == "sovereign":
        return BOND_PROXIES[("sovereign_us", "IG")] if position["country"] == "US" else None
    return BOND_PROXIES[("corporate", "HY" if position["rating"] in HY_RATINGS else "IG")]


def realised_return(rows: list[dict], start_index: int, horizon: int, ticker: str) -> float | None:
    window = rows[start_index:start_index + horizon]
    if len(window) < horizon or any(not r.get(ticker) for r in window):
        return None
    growth = 1.0
    for row in window:
        growth *= 1.0 + float(row[ticker])
    return growth - 1.0


def sleeve(portfolio) -> list[dict]:
    positions = []
    for record in portfolio.to_dict("records"):
        proxy = proxy_for(record)
        if proxy:
            positions.append({"position_id": record["position_id"], "proxy": proxy, "value": float(record["market_value_usd"])})
    return positions


def window_backtest(window: str, positions: list[dict]) -> dict:
    rows = [row for row in read_rows(DATA_DIR / "market" / COMPARISON_WINDOWS[window]["returns"]) if row["^GSPC"]]
    dates = [row["date"] for row in rows]
    stress = read_json(PROCESSED_DIR / window / "stress_results_v1.json")
    triggers = []
    for run in stress["runs"]:
        day = trading_day_for(run["detected_at"], dates)
        if day is None:
            continue
        start = dates.index(day)
        stressed = {p["position_id"]: p["pnl"] for p in run["positions"]}
        entry = {"cluster_id": run["cluster_id"], "detected_at": run["detected_at"], "trading_day": day, "stressed_sleeve_pnl": round(sum(stressed[p["position_id"]] for p in positions), 2)}
        for horizon in HORIZONS:
            returns = [realised_return(rows, start, horizon, p["proxy"]) for p in positions]
            entry[f"realised_sleeve_pnl_{horizon}d"] = round(sum(p["value"] * r for p, r in zip(positions, returns) if r is not None), 2) if all(r is not None for r in returns) else None
        triggers.append(entry)
    spec = COMPARISON_WINDOWS[window]
    in_window = [i for i, d in enumerate(dates) if spec["start"] <= d <= spec["end"]]
    unconditional = {}
    for horizon in HORIZONS:
        pnls = []
        for index in in_window:
            returns = [realised_return(rows, index, horizon, p["proxy"]) for p in positions]
            if all(r is not None for r in returns):
                pnls.append(sum(p["value"] * r for p, r in zip(positions, returns)))
        unconditional[f"{horizon}d"] = {"days": len(pnls), "share_negative": round(sum(v < 0 for v in pnls) / len(pnls), 4) if pnls else None, "mean_pnl": round(sum(pnls) / len(pnls), 2) if pnls else None}
    summary = {}
    for horizon in HORIZONS:
        key = f"realised_sleeve_pnl_{horizon}d"
        valid = [t for t in triggers if t[key] is not None]
        summary[f"{horizon}d"] = {
            "triggers": len(valid),
            "coverage_realised_loss_within_stress": round(sum(t[key] >= t["stressed_sleeve_pnl"] for t in valid) / len(valid), 4) if valid else None,
            "direction_hit_realised_negative": round(sum(t[key] < 0 for t in valid) / len(valid), 4) if valid else None,
            "mean_realised_pnl": round(sum(t[key] for t in valid) / len(valid), 2) if valid else None,
            "mean_stressed_pnl": round(sum(t["stressed_sleeve_pnl"] for t in valid) / len(valid), 2) if valid else None,
        }
    return {"triggers": triggers, "summary": summary, "unconditional_all_days": unconditional}


def backtest() -> dict:
    positions = sleeve(load_portfolio())
    return {
        "sleeve": {"positions": len(positions), "value": round(sum(p["value"] for p in positions), 2), "proxies": sorted({p["proxy"] for p in positions})},
        "horizons_trading_days": HORIZONS,
        "definitions": {
            "coverage": "share of triggers where the realised sleeve P&L was no worse than the stressed sleeve P&L (the stress bounds the realised loss)",
            "direction_hit": "share of triggers where the realised sleeve P&L was negative",
            "unconditional_all_days": "the same realised P&L measured from every trading day in the window, for comparison",
        },
        "windows": {window: window_backtest(window, positions) for window in available_windows()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=BACKTEST_PATH)
    args = parser.parse_args()
    result = backtest()
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({w: v["summary"] for w, v in result["windows"].items()}, indent=1))


if __name__ == "__main__":
    main()
