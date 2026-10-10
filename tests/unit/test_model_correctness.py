import json

import numpy as np
import pandas as pd
import pytest

from src.riskengine.config import DATA_DIR
from src.stress.portfolio_gen import black_scholes, load_portfolio, par_bond_risk
from src.stress.shocks import position_shocks, shock_config
from src.stress.valuation import capital_view, ifrs9_view, revalue


def bond_price(maturity: int, coupon: float, annual_yield: float) -> float:
    times = np.arange(1, maturity + 1, dtype=float)
    cashflows = np.full(maturity, coupon)
    cashflows[-1] += 1.0
    return float(np.sum(cashflows * (1.0 + annual_yield) ** -times))


@pytest.mark.parametrize("maturity", [2, 5, 10])
@pytest.mark.parametrize("shift_bp", [-100, -25, 25, 100, 250])
def test_duration_convexity_matches_full_cashflow_repricing(maturity, shift_bp):
    annual_yield = 0.04
    duration, convexity = par_bond_risk(maturity, annual_yield)
    move = shift_bp * 1e-4
    exact = bond_price(maturity, annual_yield, annual_yield + move) / bond_price(maturity, annual_yield, annual_yield) - 1.0
    approximate = -duration * move + 0.5 * convexity * move**2
    if abs(shift_bp) <= 100:
        assert approximate == pytest.approx(exact, abs=2e-4)
    else:
        assert approximate == pytest.approx(exact, rel=0.02)


@pytest.mark.parametrize("option_type", ["call", "put"])
@pytest.mark.parametrize(("spot_move", "vol_move"), [(-2.0, 1.0), (1.5, -1.0), (-5.0, 3.0)])
def test_delta_gamma_vega_matches_full_black_scholes_repricing(option_type, spot_move, vol_move):
    spot, strike, years, vol, rate = 100.0, 95.0, 0.5, 0.3, 0.01
    base = black_scholes(option_type, spot, strike, years, vol, rate)
    exact = black_scholes(option_type, spot + spot_move, strike, years, vol + vol_move / 100.0, rate)["price"] - base["price"]
    approximate = base["delta"] * spot_move + 0.5 * base["gamma"] * spot_move**2 + base["vega_per_vol_pt"] * vol_move
    assert approximate == pytest.approx(exact, abs=0.05 * max(1.0, abs(exact)))


def one_loan(rating: str, maturity: float = 5.0) -> pd.DataFrame:
    return pd.DataFrame([{
        "position_id": "LN1", "asset_class": "loan", "sector": "energy", "country": "RU", "rating": rating,
        "ead_usd": 100e6, "lgd": 0.45, "maturity_years": maturity, "market_value_usd": 100e6, "coupon_type": "",
        "rate_duration": 0.0, "spread_duration": 0.0, "convexity": 0.0, "dv01_usd_per_bp": 0.0, "beta": 0.0,
        "contracts": 0.0, "multiplier": 0.0, "underlying_price": 0.0, "delta": 0.0, "gamma": 0.0, "vega_per_vol_pt": 0.0,
    }])


def loan_shocks(rating_after: str, pd_before: float, pd_after: float) -> pd.DataFrame:
    return pd.DataFrame([{
        "position_id": "LN1", "rating_after": rating_after, "pd_before": pd_before, "pd_after": pd_after,
        "d_rate_bp": 0.0, "d_spread_bp": 0.0, "d_migration_spread_bp": 0.0, "equity_return": 0.0, "d_vol_pts": 0.0,
    }])


@pytest.mark.parametrize(
    ("before", "after", "stage"),
    [("BBB", "BBB", 1), ("BBB", "BBB-", 1), ("BBB+", "BB+", 2), ("A", "BBB", 2), ("BB+", "BB-", 1), ("B-", "CCC", 3)],
)
def test_ifrs9_stage_transitions(before, after, stage):
    view = ifrs9_view(one_loan(before), loan_shocks(after, 0.002, 0.01))
    assert view["stage_after"].iloc[0] == stage


def test_stage_two_provision_exceeds_twelve_month_provision():
    stage_one = revalue(one_loan("BBB"), loan_shocks("BBB-", 0.0018, 0.0030))["pnl"].iloc[0]
    stage_two = revalue(one_loan("BBB"), loan_shocks("BB", 0.0018, 0.0080))["pnl"].iloc[0]
    twelve_month_only = -100e6 * 0.45 * (0.0080 - 0.0018)
    assert stage_one < 0
    assert stage_two < twelve_month_only < 0


def test_risk_weighted_assets_rise_with_downgrade():
    portfolio = one_loan("BBB")
    assert capital_view(portfolio, loan_shocks("BB", 0.0018, 0.008))["rwa_change"] == pytest.approx(100e6 * 0.25)
    assert capital_view(portfolio, loan_shocks("BBB", 0.0018, 0.0018))["rwa_change"] == 0.0


def test_safe_haven_sovereigns_get_no_spread_widening():
    portfolio = load_portfolio()
    for scenario in ("geopolitical", "credit_event"):
        shocks = position_shocks(portfolio, scenario, 9.0, "macro", [])
        safe = portfolio["sector"].eq("sovereign") & portfolio["rating"].isin(["AAA", "AA+", "AA", "AA-"])
        assert safe.any()
        assert (shocks.loc[safe.to_numpy(), "d_spread_bp"] <= 0).all()


def test_contagion_changes_which_positions_are_hit():
    portfolio = load_portfolio()
    russia = position_shocks(portfolio, "geopolitical", 9.0, "country", ["country:RU"])
    taiwan = position_shocks(portfolio, "geopolitical", 9.0, "country", ["country:TW"])
    poland = portfolio["country"].eq("PL").to_numpy()
    assert (russia.loc[poland, "contagion_weight"] > 0).all()
    assert (taiwan.loc[poland, "contagion_weight"] == 0).all()
    assert russia["d_spread_bp"].sum() != taiwan["d_spread_bp"].sum()


def test_shock_config_is_tied_to_the_calibration_file():
    calibration = json.loads((DATA_DIR / "market" / "shock_calibration.json").read_text(encoding="utf-8"))
    scenarios = shock_config()["scenarios"]
    for name, entry in calibration["scenarios"].items():
        base = entry["base_shock"]
        assert scenarios[name]["equity_market"] == pytest.approx(base["equity_market"])
        assert scenarios[name]["rates_bp"] == pytest.approx(base["rates_bp"])
        assert scenarios[name]["vol_pts"] == pytest.approx(base["vol_pts"])
        assert {k: v for k, v in scenarios[name]["spread_bp"].items() if k != "SAFE"} == base["spread_bp"]
        assert scenarios[name]["sector_excess"] == pytest.approx(base["sector_excess"])
