import json
from pathlib import Path

from src.stress.engine import run_stress
from src.stress.portfolio_gen import load_portfolio

GOLDEN_DIR = Path(__file__).resolve().parent


def golden_summary(run: dict) -> dict:
    return {
        "multiplier": run["shocks_applied"]["multiplier"],
        "in_scope_positions": sorted(p["position_id"] for p in run["positions"] if p["in_scope"]),
        "total_pnl": run["totals"]["pnl"],
        "by_asset_class": {a["asset_class"]: a["pnl"] for a in run["by_asset_class"]},
        "by_factor": run["by_factor"],
        "loan_loss_views": run["loan_loss_views"],
    }


def compute_all() -> dict:
    portfolio = load_portfolio()
    scenarios = json.loads((GOLDEN_DIR / "scenarios.json").read_text(encoding="utf-8"))
    return {event["cluster_id"]: golden_summary(run_stress(portfolio, event, {})) for event in scenarios}


if __name__ == "__main__":
    (GOLDEN_DIR / "expected.json").write_text(json.dumps(compute_all(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("golden expectations written")
