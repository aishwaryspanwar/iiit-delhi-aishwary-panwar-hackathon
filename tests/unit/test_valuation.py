import numpy as np
import pandas as pd
import pytest

from src.stress.portfolio_gen import COLUMNS, par_bond_risk
from src.stress.shocks import downgraded_ratings, severity_multiplier
from src.stress.valuation import FACTORS, lifetime_pd, loan_lifetime_el_change, revalue


def position(**fields) -> dict:
    row = {column: "" for column in COLUMNS}
    numeric = ["notional_usd", "market_value_usd", "maturity_years", "ead_usd", "lgd", "rate_duration", "spread_duration", "convexity", "dv01_usd_per_bp", "beta",
               "contracts", "multiplier", "underlying_price", "strike", "expiry_years", "implied_vol", "delta", "gamma", "vega_per_vol_pt"]
    row.update({column: 0.0 for column in numeric})
    row.update(fields)
    return row


def shock(**fields) -> dict:
    base = {"position_id": "P", "in_scope": False, "d_rate_bp": 0.0, "d_spread_bp": 0.0, "rating_notches": 0, "rating_after": "",
            "d_migration_spread_bp": 0.0, "pd_before": 0.0, "pd_after": 0.0, "equity_return": 0.0, "d_vol_pts": 0.0}
    base.update(fields)
    return base


def value_one(pos: dict, shk: dict) -> pd.Series:
    return revalue(pd.DataFrame([pos]), pd.DataFrame([shk])).iloc[0]


FIXED_BOND = position(position_id="P", asset_class="bond", coupon_type="fixed", market_value_usd=100e6, rate_duration=5.0, spread_duration=5.0, convexity=30.0)
FRN = position(position_id="P", asset_class="bond", coupon_type="frn", market_value_usd=100e6, rate_duration=0.25, spread_duration=5.0, convexity=30.0)
LOAN = position(position_id="P", asset_class="loan", market_value_usd=100e6, ead_usd=100e6, lgd=0.45)
PAYER = position(position_id="P", asset_class="irs", direction="payer", dv01_usd_per_bp=40_000.0)
RECEIVER = position(position_id="P", asset_class="irs", direction="receiver", dv01_usd_per_bp=-40_000.0)
EQUITY = position(position_id="P", asset_class="equity", market_value_usd=50e6, beta=1.2)
LONG_PUT = position(position_id="P", asset_class="option", option_type="put", contracts=1000.0, multiplier=100.0, underlying_price=100.0, delta=-0.4, gamma=0.02, vega_per_vol_pt=0.2, market_value_usd=500_000.0)
LONG_CALL = position(position_id="P", asset_class="option", option_type="call", contracts=1000.0, multiplier=100.0, underlying_price=100.0, delta=0.5, gamma=0.02, vega_per_vol_pt=0.2, market_value_usd=600_000.0)
SHORT_CALL = position(position_id="P", asset_class="option", option_type="call", contracts=-1000.0, multiplier=100.0, underlying_price=100.0, delta=0.5, gamma=0.02, vega_per_vol_pt=0.2, market_value_usd=-600_000.0)


def test_fixed_bond_loses_when_rates_rise():
    result = value_one(FIXED_BOND, shock(d_rate_bp=100))
    assert result["rates"] == pytest.approx(-100e6 * 5.0 * 0.01)
    assert result["second_order"] == pytest.approx(0.5 * 100e6 * 30.0 * 0.01**2)
    assert result["pnl"] < 0


def test_bond_gains_when_rates_fall():
    assert value_one(FIXED_BOND, shock(d_rate_bp=-50))["rates"] > 0


def test_frn_rate_sensitivity_is_small_but_spread_sensitivity_full():
    frn = value_one(FRN, shock(d_rate_bp=100, d_spread_bp=100))
    assert frn["rates"] == pytest.approx(-100e6 * 0.25 * 0.01)
    assert frn["spread"] == pytest.approx(-100e6 * 5.0 * 0.01)


def test_spread_widening_and_migration_hurt_bond():
    result = value_one(FIXED_BOND, shock(d_spread_bp=100, d_migration_spread_bp=50))
    assert result["spread"] < 0
    assert result["migration"] == pytest.approx(-100e6 * 5.0 * 0.005)


def test_loan_downgrade_increases_expected_loss():
    result = value_one(LOAN, shock(pd_before=0.002, pd_after=0.008))
    assert result["migration"] == pytest.approx(-100e6 * 0.45 * 0.006)
    assert result["rates"] == 0 and result["spread"] == 0


def test_swap_signs():
    assert value_one(PAYER, shock(d_rate_bp=10))["rates"] == pytest.approx(400_000)
    assert value_one(RECEIVER, shock(d_rate_bp=10))["rates"] == pytest.approx(-400_000)


def test_equity_return_applied_to_value():
    assert value_one(EQUITY, shock(equity_return=-0.1))["equity"] == pytest.approx(-5e6)


def test_option_delta_gamma_vega():
    result = value_one(LONG_PUT, shock(equity_return=-0.10, d_vol_pts=10))
    assert result["equity"] == pytest.approx(1000 * 100 * -0.4 * -10.0)
    assert result["second_order"] == pytest.approx(0.5 * 1000 * 100 * 0.02 * 100.0)
    assert result["vol"] == pytest.approx(1000 * 100 * 0.2 * 10)
    assert result["pnl"] > 0


def test_option_signs_in_a_selloff():
    selloff = shock(equity_return=-0.10, d_vol_pts=10)
    assert value_one(LONG_CALL, selloff)["equity"] < 0
    assert value_one(LONG_CALL, selloff)["vol"] > 0
    assert value_one(SHORT_CALL, selloff)["vol"] < 0
    assert value_one(SHORT_CALL, selloff)["second_order"] < 0


@pytest.mark.parametrize("pos", [FIXED_BOND, FRN, LOAN, PAYER, RECEIVER, EQUITY, LONG_PUT, SHORT_CALL])
def test_zero_shock_zero_pnl(pos):
    result = value_one(pos, shock())
    assert result["pnl"] == 0
    assert result["value_after"] == result["value_before"]


def test_par_bond_duration_matches_closed_form():
    duration, convexity = par_bond_risk(10, 0.04)
    assert duration == pytest.approx((1 - 1.04**-10) / 0.04, abs=1e-3)
    assert convexity > duration


def test_severity_multiplier_range():
    assert severity_multiplier(7.0) == 0.5
    assert severity_multiplier(10.0) == 1.0
    assert severity_multiplier(8.5) == 0.75


def test_downgrade_caps_at_worst_rating():
    ratings = pd.Series(["BBB", "B-", "CCC"])
    assert downgraded_ratings(ratings, np.array([2, 3, 1])).tolist() == ["BB+", "CCC", "CCC"]


def test_factors_sum_to_pnl():
    frame = pd.DataFrame([FIXED_BOND, LOAN, PAYER, EQUITY]).assign(position_id=["A", "B", "C", "D"])
    shocks = pd.DataFrame([shock(position_id=p, d_rate_bp=30, d_spread_bp=80, pd_before=0.002, pd_after=0.005, equity_return=-0.08) for p in "ABCD"])
    result = revalue(frame, shocks)
    assert np.allclose(result[FACTORS].sum(axis=1), result["pnl"])


def test_lifetime_pd_compounds_and_exceeds_one_year():
    assert lifetime_pd(np.array([0.01]), np.array([5.0]))[0] == pytest.approx(1 - 0.99**5)
    assert lifetime_pd(np.array([0.01]), np.array([0.5]))[0] == pytest.approx(0.01)


def test_lifetime_el_change_is_larger_than_one_year_for_multi_year_loans():
    frame = pd.DataFrame([{**LOAN, "maturity_years": 5.0}])
    shocks = pd.DataFrame([shock(pd_before=0.005, pd_after=0.013)])
    one_year = revalue(frame, shocks)["migration"].iloc[0]
    lifetime = loan_lifetime_el_change(frame, shocks)
    assert lifetime < one_year < 0
