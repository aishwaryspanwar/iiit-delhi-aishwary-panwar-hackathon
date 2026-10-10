import pandas as pd
import streamlit as st

from src.api.service import alerts, evaluation

SPLIT_LABELS = {"w1_dev": "W1 development (LLM labels)", "w1_test": "W1 test (human-verified)", "w3_test": "W3 test (human-verified)"}


def interval(values: list[float] | None) -> str:
    return f"[{values[0]:.2f}, {values[1]:.2f}]" if values else ""


def classification_frame(metrics: dict) -> pd.DataFrame:
    rows = []
    for split, report in metrics["splits"].items():
        r = report["representative"]
        rows.append({
            "Split": SPLIT_LABELS.get(split, split),
            "Items (human-verified)": f"{r['n']} ({r['human_verified']})",
            "Event class macro-F1": f"{r['event_class']['macro_f1']:.2f} {interval(r['event_class'].get('macro_f1_ci95'))}",
            "Keyword baseline": f"{r['event_class_naive_keywords']['macro_f1']:.2f}",
            "Majority baseline": f"{r['event_class']['majority_macro_f1']:.2f}",
            "FinBERT sentiment macro-F1": f"{r['sentiment_finbert']['macro_f1']:.2f} {interval(r['sentiment_finbert'].get('macro_f1_ci95'))}",
            "VADER sentiment macro-F1": f"{r['sentiment_vader']['macro_f1']:.2f}",
        })
    return pd.DataFrame(rows)


def correlation_frame(metrics: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"Window": window, "Days": values["abs_sp500"]["n"], **{label: f"{values[key]['rho']:+.2f} {interval(values[key]['ci95'])}" for key, label in (("abs_sp500", "|S&P 500 move|"), ("vix_change", "VIX change"), ("abs_rate_change", "|10y change|"))}}
        for window, values in metrics["impact_vs_market"].items()
    ])


def quality(q: dict) -> str:
    precision = "n/a" if q["precision"] is None else f"{q['precision']:.0%}"
    recall = "n/a" if q["recall"] is None else f"{q['recall']:.0%}"
    return f"{q['flags']} flags · precision {precision} · recall {recall}"


def trigger_frame(metrics: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"Window": window, "Stress days": f"{q['stress_days']} of {q['trading_days']}", "Engine alerts": quality(q["engine_alerts"]),
         "Impact > 7, no gates": quality(q["impact_above_7_without_gates"]), "Headline-volume spike": quality(q["naive_headline_volume_spike"])}
        for window, q in metrics["trigger_quality"].items()
    ])


def render(dataset: str) -> None:
    st.subheader("Real-time alerts")
    rows = alerts(dataset)
    if rows:
        st.dataframe(pd.DataFrame([{
            "detected_at": a["detected_at"], "first_headline_at": a["first_headline_at"], "class": a["class"], "scope": a["scope_label"],
            "impact": a["impact"], "stress_pnl_musd": None if a["pnl"] is None else a["pnl"] / 1e6, "lead": (a["lead"] or {}).get("text"),
        } for a in rows]), width="stretch", hide_index=True)
    else:
        st.info("No alert fired in this window.")
    data = evaluation()
    metrics = data["metrics"]
    st.subheader("Evaluation")
    if not metrics:
        st.warning("No evaluation yet. Run: python -m scripts.evaluate")
        return
    st.caption(f"Engine {metrics['engine_version']}, config {metrics['config_hash']}. Brackets are 95% bootstrap intervals. Test sets were never used for tuning.")
    st.dataframe(classification_frame(metrics), width="stretch", hide_index=True)
    blind = metrics["llm_vs_human_blind"]
    if blind.get("n"):
        st.caption(f"LLM annotator against a person on {blind['n']} blind items: event class agreement {blind['event_class_agreement']:.0%} (kappa {blind['event_class_kappa']:.2f}), sentiment {blind['sentiment_agreement']:.0%} (kappa {blind['sentiment_kappa']:.2f}).")
    st.markdown("**Does impact track the market?** Spearman correlation of the daily maximum event impact with same-day moves.")
    st.dataframe(correlation_frame(metrics), width="stretch", hide_index=True)
    st.markdown(f"**Trigger quality.** {metrics['definitions']['stress_day']}.")
    st.dataframe(trigger_frame(metrics), width="stretch", hide_index=True)
    if data["backtest"]:
        st.markdown("**Stress backtest** on the liquid sleeve (equities and bond ETF proxies).")
        st.dataframe(pd.DataFrame([{"window": w, **t} for w, v in data["backtest"]["windows"].items() for t in v["triggers"]]), width="stretch", hide_index=True)
