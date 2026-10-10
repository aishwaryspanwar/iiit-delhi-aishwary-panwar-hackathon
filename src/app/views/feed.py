import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.data import load_events, load_signals, load_stress
from src.app.theme import STATUS_COLORS, style_figure
from src.stress.trigger import EVENT_STATUS_LABELS, event_status as status_key

FEED_COLUMNS = ["published_at", "source", "outlet", "text", "event_class", "confidence", "sentiment", "impact", "scope", "targets", "rules", "mentions"]


def event_status(events: pd.DataFrame, stress: dict) -> pd.Series:
    triggered = {d["cluster_id"] for d in stress["decisions"] if d["triggered"]}
    threshold = stress["trigger_settings"]["impact_threshold"]
    return events.apply(lambda e: EVENT_STATUS_LABELS[status_key(e, triggered, threshold)], axis=1)


def impact_timeline(events: pd.DataFrame, threshold: float, cutoff: pd.Timestamp) -> go.Figure:
    figure = go.Figure()
    for status, color in STATUS_COLORS.items():
        subset = events[events["status"] == status]
        figure.add_trace(go.Scatter(
            x=subset["t_start"], y=subset["impact"], mode="markers", name=status,
            marker={"size": 8 + subset["n_items"].clip(upper=12) * 1.5, "color": color, "line": {"width": 2, "color": "rgba(252,252,251,0.9)"}},
            customdata=subset[["class_name", "scope", "n_items", "n_outlets", "confidence_mean", "sentiment_mean", "severity", "breadth", "abnormal_volume", "target"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}: %{customdata[9]}<br>Impact %{y:.1f} · %{customdata[2]} items · %{customdata[3]} outlets"
                          "<br>Severity %{customdata[6]:.2f} · Breadth %{customdata[7]:.2f} · Abnormal volume %{customdata[8]:.2f}"
                          "<br>Confidence %{customdata[4]:.2f} · Sentiment %{customdata[5]:+.2f}<br>%{x|%d %b %Y}<extra></extra>",
        ))
    figure.add_hline(y=threshold, line={"color": "#898781", "width": 1, "dash": "dot"}, annotation_text=f"Trigger threshold > {threshold:g}", annotation_position="top left")
    figure.add_vline(x=cutoff, line={"color": "#898781", "width": 1})
    figure.update_yaxes(range=[0.5, 10.5], title="Event impact (1–10)")
    figure.update_xaxes(title=None)
    return style_figure(figure, 380)


def render(dataset: str) -> None:
    signals = load_signals(dataset)
    events = load_events(dataset)
    stress = load_stress(dataset)
    events["status"] = event_status(events, stress)
    components = pd.DataFrame(events["impact_components"].tolist(), index=events.index)
    events = events.join(components)
    events["target"] = events["scope_targets"].map(lambda targets: targets[0] if targets else "none")
    days = sorted(signals["published_at"].dt.normalize().unique())
    st.subheader("Signal feed — replay")
    st.caption("Historical replay: the scrubber moves the clock forward; only signals published up to that day are shown.")
    replay_day = st.select_slider("Replay up to", options=days, value=days[-1], format_func=lambda d: pd.Timestamp(d).strftime("%d %b %Y"))
    cutoff = pd.Timestamp(replay_day) + pd.Timedelta(days=1)
    visible_signals = signals[signals["published_at"] < cutoff]
    visible_events = events[events["t_start"] < cutoff]
    left, middle, right, fourth = st.columns(4)
    left.metric("Signals", f"{len(visible_signals):,}")
    middle.metric("Event clusters", f"{len(visible_events):,}")
    right.metric("Stress tests triggered", int((visible_events["status"] == "Triggered stress test").sum()))
    fourth.metric("Sources", visible_signals["source"].nunique())
    st.plotly_chart(impact_timeline(visible_events, stress["trigger_settings"]["impact_threshold"], cutoff), width="stretch", theme="streamlit")
    filters = st.columns(3)
    classes = filters[0].multiselect("Event class", sorted(signals["event_class"].unique()))
    sources = filters[1].multiselect("Source", sorted(signals["source"].unique()))
    min_impact = filters[2].slider("Minimum item impact", 1.0, 10.0, 1.0, 0.5)
    table = visible_signals
    if classes:
        table = table[table["event_class"].isin(classes)]
    if sources:
        table = table[table["source"].isin(sources)]
    table = table[table["impact"] >= min_impact].sort_values("published_at", ascending=False)
    st.dataframe(
        table[FEED_COLUMNS],
        width="stretch",
        hide_index=True,
        column_config={
            "published_at": st.column_config.DatetimeColumn("Published (UTC)", format="DD MMM YYYY HH:mm"),
            "text": st.column_config.TextColumn("Text", width="large"),
            "sentiment": st.column_config.NumberColumn("Sentiment", format="%+.2f"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
            "impact": st.column_config.ProgressColumn("Impact", min_value=1, max_value=10, format="%.1f"),
        },
    )
