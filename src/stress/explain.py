from src.riskengine.entities import SCOPE_BY_TYPE, entity_table
from src.riskengine.events import class_display_name


def format_musd(value: float) -> str:
    return f"{value / 1e6:+,.1f}m"


def scope_target_names(event: dict) -> str:
    table = entity_table()
    names = [table[t]["name"] for t in event["scope_targets"] if t in table and SCOPE_BY_TYPE[table[t]["type"]] == event["scope"]]
    refinements = [table[t]["name"] for t in event["scope_targets"] if t in table and event["scope"] == "country" and table[t]["type"] in ("sector", "commodity")]
    label = ", ".join(names) or "no specific target"
    return f"{label} ({', '.join(refinements)})" if refinements else label


def explanation_text(event: dict, signals_by_id: dict[str, dict], summary: dict, totals: dict, top_losses: list[dict]) -> str:
    lead = signals_by_id.get(event["representative_signal_ids"][0], {})
    rules = sorted({r for sid in event["representative_signal_ids"] for r in signals_by_id.get(sid, {}).get("event", {}).get("matched_rules", [])})
    headline = lead.get("text") or f"signal {lead.get('signal_id', 'n/a')}"
    origin = lead.get("outlet") or lead.get("source", "unknown source")
    scope_line = scope_target_names(event)
    loss_line = "; ".join(f"{row['position_id']} {row['name']} {format_musd(row['pnl'])}" for row in top_losses) or "none"
    return (
        f"Triggered by a {class_display_name(event['class'])} event with impact {event['impact']:.1f}/10 "
        f"(confidence {event['confidence_mean']:.2f}, sentiment {event['sentiment_mean']:+.2f}) built from "
        f"{event['n_items']} item(s) across {event['n_outlets']} outlet(s). "
        f"Matched rules: {', '.join(rules) or 'none'}. "
        f"Lead item: \"{headline}\" ({origin}, {lead.get('published_at', '')[:10]}). "
        f"Scope: {event['scope']} -> {scope_line}. "
        f"Shocks at severity multiplier {summary['multiplier']:.2f}: equities {summary['equity_market']:+.1%} x beta, "
        f"rates {summary['rates_bp']:+.0f}bp, IG spreads {summary['spread_bp']['IG']:+.0f}bp, HY spreads {summary['spread_bp']['HY']:+.0f}bp, "
        f"in-scope add-on {summary['in_scope']['spread_bp']:+.0f}bp and {summary['in_scope']['rating_notches']} notch downgrade(s). "
        f"Portfolio value moves {format_musd(totals['pnl'])} ({totals['pnl_pct']:+.2%}). Largest losses: {loss_line}."
    )
