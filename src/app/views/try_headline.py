import pandas as pd
import streamlit as st

from src.app.views.stress import musd

from src.riskengine.build import score_single_text
from src.riskengine.events import class_display_name
from src.riskengine.sentiment.vader import VaderSentiment
from src.stress.engine import run_stress
from src.stress.portfolio_gen import load_portfolio
from src.stress.shocks import shock_config
from src.stress.trigger import CHECK_LABELS, condition_checks
from src.stress.whatif import EXAMPLES, MAX_LENGTH, OUTLET_RANGE, VOLUME_OPTIONS, what_if_event


@st.cache_resource(show_spinner=False)
def sentiment_model() -> VaderSentiment:
    return VaderSentiment()


@st.cache_data(show_spinner=False)
def portfolio() -> pd.DataFrame:
    return load_portfolio()


def render_signal(signal: dict) -> None:
    cols = st.columns(4)
    cols[0].metric("Event class", class_display_name(signal["event"]["class"]))
    cols[1].metric("Confidence", f"{signal['event']['confidence']:.2f}")
    cols[2].metric("Sentiment", f"{signal['sentiment']['score']:+.2f}", help=signal["sentiment"]["model"])
    cols[3].metric("Item impact", f"{signal['impact']['score']:.1f} / 10")
    st.caption(f"Matched rules: {', '.join(signal['event']['matched_rules']) or 'none'} · runner-up class: {signal['event']['runner_up'] or 'none'}")
    left, right = st.columns(2)
    left.markdown("**Impact components** (each 0–1)")
    left.dataframe(pd.DataFrame([signal["impact"]["components"]]).T.rename(columns={0: "value"}), width="stretch")
    right.markdown(f"**Entities** · scope: `{signal['scope']}`")
    entities = pd.DataFrame(signal["entities"]) if signal["entities"] else pd.DataFrame(columns=["id", "name", "type", "matched"])
    right.dataframe(entities[["id", "name", "type", "matched"]], width="stretch", hide_index=True)


def render() -> None:
    st.subheader("Try a headline")
    st.caption("Runs the same rule engine live (VADER + finance lexicon sentiment; no model download, no network). The precomputed feed may use a different sentiment model — see evaluation.")
    example = st.selectbox("Start from an example, or type your own below", ["(type your own)"] + EXAMPLES)
    default_text = "" if example == "(type your own)" else example
    text = st.text_area("Headline or post", value=default_text, max_chars=MAX_LENGTH, height=80)
    if not text.strip():
        st.info("Enter a headline to score it.")
        return
    try:
        result = score_single_text(text, sentiment_model())
    except ValueError:
        st.warning("Nothing left to score after cleaning (links and handles are removed).")
        return
    st.markdown("**Cleaned text**")
    st.text(result["signal"]["text"])
    render_signal(result["signal"])
    st.divider()
    st.markdown("**Would this trigger a stress test?** A single item is never enough on its own — set how widely the story is being reported:")
    left, right = st.columns(2)
    outlets = left.slider("Distinct news outlets reporting", OUTLET_RANGE[0], OUTLET_RANGE[1], 1)
    volume = right.select_slider("Mentions vs the topic's normal daily volume", options=VOLUME_OPTIONS, value=1.0, format_func=lambda v: f"{v:g}×")
    event = what_if_event(result, outlets, volume)
    checks = condition_checks(event, shock_config()["trigger"])
    st.metric("Event impact (what-if)", f"{event['impact']:.1f} / 10", help=str(event["impact_components"]))
    st.dataframe(pd.DataFrame([{"check": CHECK_LABELS[k], "passed": v} for k, v in checks.items()]), width="stretch", hide_index=True)
    triggered = all(checks.values())
    preview = triggered or st.toggle("Preview the stress test anyway", value=False)
    if triggered:
        st.success("All trigger conditions met — the stress test below would run automatically.")
    if not preview:
        return
    if event["class"] not in shock_config()["scenarios"]:
        st.info(f"No stress scenario is defined for {class_display_name(event['class'])} events.")
        return
    run = run_stress(portfolio(), event, {result["signal"]["signal_id"]: result["signal"]})
    totals = run["totals"]
    cols = st.columns(3)
    cols[0].metric("Stress P&L (preview)", musd(totals["pnl"]), delta=f"{totals['pnl_pct']:+.2%}")
    cols[1].metric("In-scope positions", run["in_scope_positions"])
    cols[2].metric("Severity multiplier", f"{run['shocks_applied']['multiplier']:.2f}")
    st.text(run["explanation"])
