import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.data import load_stress
from src.app.theme import NEGATIVE, NEUTRAL, POSITIVE, style_figure
from src.riskengine.events import class_display_name

DISCLAIMER = "Illustrative model on a synthetic portfolio — not a regulatory stress test and not investment advice. Ratings, PDs and sensitivities are synthetic."
FACTOR_LABELS = {"rates": "Rates", "spread": "Credit spread", "migration": "Rating migration", "equity": "Equity", "vol": "Volatility", "second_order": "Convexity (2nd order)"}
ASSET_LABELS = {"loan": "Loans", "bond": "Bonds", "irs": "Interest-rate swaps", "equity": "Equities", "option": "Equity options"}


def musd(value: float) -> str:
    sign = "−" if value < 0 else ""
    return f"{sign}${abs(value) / 1e6:,.1f}m"


def run_label(run: dict) -> str:
    return f"{run['t_start'][:10]} · {class_display_name(run['class'])} · impact {run['impact']:.1f} · {run['scope']}: {', '.join(run['scope_targets'][:2])}"


def asset_impact_chart(by_asset: pd.DataFrame) -> go.Figure:
    frame = by_asset.assign(label=by_asset["asset_class"].map(ASSET_LABELS), pct=by_asset["pnl"] / by_asset["value_before"].abs().where(by_asset["value_before"].abs() > 0))
    frame = frame.sort_values("pnl")
    colors = [NEGATIVE if v < 0 else POSITIVE for v in frame["pnl"]]
    figure = go.Figure(go.Bar(
        x=frame["pnl"] / 1e6, y=frame["label"], orientation="h", marker={"color": colors, "cornerradius": 4},
        text=[f"{v / 1e6:+,.1f}m" for v in frame["pnl"]], textposition="outside",
        customdata=frame[["value_before", "value_after", "pct"]].fillna(0).to_numpy() / [1e6, 1e6, 1],
        hovertemplate="<b>%{y}</b><br>Before $%{customdata[0]:,.1f}m → after $%{customdata[1]:,.1f}m<br>P&L %{x:+,.1f}m (%{customdata[2]:+.2%})<extra></extra>",
    ))
    figure.add_vline(x=0, line={"color": "#c3c2b7", "width": 1})
    figure.update_layout(title="Stress P&L by asset class (USD m)", showlegend=False)
    return style_figure(figure, 340)


def factor_waterfall(by_factor: dict, total: float) -> go.Figure:
    names = [FACTOR_LABELS[k] for k in FACTOR_LABELS if k in by_factor]
    values = [by_factor[k] / 1e6 for k in FACTOR_LABELS if k in by_factor]
    figure = go.Figure(go.Waterfall(
        x=names + ["Total P&L"], y=values + [total / 1e6], measure=["relative"] * len(values) + ["total"],
        increasing={"marker": {"color": POSITIVE}}, decreasing={"marker": {"color": NEGATIVE}}, totals={"marker": {"color": NEUTRAL}},
        connector={"line": {"color": "rgba(137,135,129,0.4)", "width": 1}},
        text=[f"{v:+,.1f}" for v in values + [total / 1e6]], textposition="outside",
        hovertemplate="%{x}<br>%{y:+,.1f}m<extra></extra>",
    ))
    figure.update_layout(title="P&L attribution by risk factor (USD m)", showlegend=False)
    return style_figure(figure, 340)


def position_table(run: dict) -> pd.DataFrame:
    frame = pd.DataFrame(run["positions"])
    frame["asset_class"] = frame["asset_class"].map(ASSET_LABELS)
    frame["pnl_musd"] = frame["pnl"] / 1e6
    frame["value_before_musd"] = frame["value_before"] / 1e6
    columns = ["position_id", "asset_class", "name", "sector", "country", "rating", "rating_after", "in_scope", "value_before_musd", "pnl_musd", "d_rate_bp", "d_spread_bp", "equity_return"]
    return frame.sort_values("pnl")[columns]


def shock_table(summary: dict) -> pd.DataFrame:
    rows = [
        ("Severity multiplier", f"{summary['multiplier']:.2f}"),
        ("Equity market (× beta)", f"{summary['equity_market']:+.1%}"),
        ("Risk-free rates", f"{summary['rates_bp']:+.0f} bp"),
        ("IG spreads", f"{summary['spread_bp']['IG']:+.0f} bp"),
        ("HY spreads", f"{summary['spread_bp']['HY']:+.0f} bp"),
        ("Implied volatility", f"{summary['vol_pts']:+.1f} pts"),
        ("In-scope spread add-on", f"{summary['in_scope']['spread_bp']:+.0f} bp"),
        ("In-scope rating downgrade", f"{summary['in_scope']['rating_notches']} notch(es)"),
        ("In-scope equity excess", f"{summary['in_scope']['equity_excess']:+.1%}"),
    ]
    rows += [(f"Sector excess: {sector}", f"{value:+.1%}") for sector, value in summary["sector_excess"].items()]
    return pd.DataFrame(rows, columns=["Shock", "Applied"])


def render(dataset: str) -> None:
    stress = load_stress(dataset)
    st.subheader("Event-driven stress test")
    st.info(DISCLAIMER)
    runs = stress["runs"]
    if not runs:
        st.warning("No event in this dataset met the trigger conditions.")
        return
    choice = st.selectbox("Triggered event", range(len(runs)), format_func=lambda i: run_label(runs[i]))
    run = runs[choice]
    totals = run["totals"]
    cols = st.columns(4)
    cols[0].metric("Portfolio value before", musd(totals["value_before"]))
    cols[1].metric("After stress", musd(totals["value_after"]), delta=f"{totals['pnl_pct']:+.2%}")
    cols[2].metric("Stress P&L", musd(totals["pnl"]))
    cols[3].metric("In-scope positions", run["in_scope_positions"])
    loan_views = run["loan_loss_views"]
    st.caption(
        f"Loans are held at amortised cost: their P&L is the change in 1-year expected loss from rating migration ({musd(loan_views['one_year_el_change'])}). "
        f"On a lifetime-EL view (IFRS 9 stage-2 style sensitivity) the same downgrades cost {musd(loan_views['lifetime_el_change'])}."
    )
    st.text(run["explanation"])
    by_asset = pd.DataFrame(run["by_asset_class"])
    left, right = st.columns(2)
    left.plotly_chart(asset_impact_chart(by_asset), width="stretch", theme="streamlit")
    right.plotly_chart(factor_waterfall(run["by_factor"], totals["pnl"]), width="stretch", theme="streamlit")
    tab_positions, tab_shocks, tab_assets = st.tabs(["Positions", "Shocks applied", "By asset class"])
    tab_positions.dataframe(
        position_table(run), width="stretch", hide_index=True,
        column_config={
            "value_before_musd": st.column_config.NumberColumn("Value before (USD m)", format="%.1f"),
            "pnl_musd": st.column_config.NumberColumn("P&L (USD m)", format="%+.2f"),
            "equity_return": st.column_config.NumberColumn("Equity return", format="%+.3f"),
        },
    )
    tab_shocks.dataframe(shock_table(run["shocks_applied"]), width="stretch", hide_index=True)
    assets = by_asset.assign(asset_class=by_asset["asset_class"].map(ASSET_LABELS))
    tab_assets.dataframe(assets, width="stretch", hide_index=True)
    with st.expander("All trigger decisions"):
        st.dataframe(pd.DataFrame([{"cluster_id": d["cluster_id"], "triggered": d["triggered"], "failed_checks": ", ".join(d["failed"])} for d in stress["decisions"]]), width="stretch", hide_index=True)
