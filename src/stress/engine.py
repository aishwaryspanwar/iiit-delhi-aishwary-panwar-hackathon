import pandas as pd

from src.stress.explain import explanation_text
from src.stress.shocks import position_shocks, scenario_summary, shock_config
from src.stress.trigger import evaluate_triggers
from src.stress.valuation import FACTORS, loan_lifetime_el_change, revalue

POSITION_FIELDS = ["position_id", "asset_class", "name", "sector", "country", "rating", "ticker"]


def rounded(value: float) -> float:
    return round(float(value), 2) + 0.0


def grouped_totals(frame: pd.DataFrame, column: str) -> list[dict]:
    grouped = frame.groupby(column, sort=True)[["value_before", "value_after", "pnl"] + FACTORS].sum()
    return [{column: key, **{k: rounded(v) for k, v in row.items()}} for key, row in grouped.iterrows()]


def run_stress(portfolio: pd.DataFrame, event: dict, signals_by_id: dict[str, dict]) -> dict:
    shocks = position_shocks(portfolio, event["class"], event["impact"], event["scope"], event["scope_targets"])
    valued = revalue(portfolio, shocks)
    detail = portfolio[POSITION_FIELDS].merge(valued.drop(columns=["asset_class"]), on="position_id").merge(
        shocks[["position_id", "in_scope", "d_rate_bp", "d_spread_bp", "d_migration_spread_bp", "rating_notches", "rating_after", "equity_return"]],
        on="position_id",
    )
    before = float(valued["value_before"].sum())
    pnl = float(valued["pnl"].sum())
    totals = {"value_before": rounded(before), "value_after": rounded(before + pnl), "pnl": rounded(pnl), "pnl_pct": round(pnl / before, 6)}
    summary = scenario_summary(event["class"], event["impact"])
    top_losses = detail.sort_values(["pnl", "position_id"]).head(3)[["position_id", "name", "pnl"]].to_dict("records")
    loan_views = {
        "one_year_el_change": rounded(valued.loc[valued["asset_class"] == "loan", "migration"].sum()),
        "lifetime_el_change": rounded(loan_lifetime_el_change(portfolio, shocks)),
    }
    positions = []
    for record in detail.sort_values("position_id").to_dict("records"):
        positions.append({k: (rounded(v) if isinstance(v, float) else (bool(v) if k == "in_scope" else v)) for k, v in record.items()})
    return {
        "cluster_id": event["cluster_id"],
        "class": event["class"],
        "impact": event["impact"],
        "scope": event["scope"],
        "scope_targets": event["scope_targets"],
        "t_start": event["t_start"],
        "shocks_applied": summary,
        "in_scope_positions": int(detail["in_scope"].sum()),
        "totals": totals,
        "by_asset_class": grouped_totals(valued, "asset_class"),
        "by_factor": {factor: rounded(valued[factor].sum()) for factor in FACTORS},
        "loan_loss_views": loan_views,
        "positions": positions,
        "explanation": explanation_text(event, signals_by_id, summary, totals, top_losses, loan_views),
    }


def run_all(portfolio: pd.DataFrame, events: list[dict], signals: list[dict]) -> dict:
    decisions = evaluate_triggers(events)
    by_cluster = {e["cluster_id"]: e for e in events}
    signals_by_id = {s["signal_id"]: s for s in signals}
    runs = [run_stress(portfolio, by_cluster[d["cluster_id"]], signals_by_id) for d in decisions if d["triggered"]]
    return {
        "shocks_version": shock_config()["shocks_version"],
        "trigger_settings": shock_config()["trigger"],
        "decisions": decisions,
        "runs": runs,
    }
