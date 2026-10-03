import numpy as np
import pandas as pd

FACTORS = ["rates", "spread", "migration", "equity", "vol", "second_order"]
BP = 1e-4


def revalue(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> pd.DataFrame:
    asset = portfolio["asset_class"].to_numpy()
    value = portfolio["market_value_usd"].to_numpy()
    is_bond = asset == "bond"
    is_loan = asset == "loan"
    is_irs = asset == "irs"
    is_equity = asset == "equity"
    is_option = asset == "option"
    is_fixed = (portfolio["coupon_type"] == "fixed").to_numpy()
    d_rate = shocks["d_rate_bp"].to_numpy()
    d_spread = shocks["d_spread_bp"].to_numpy()
    d_migration = shocks["d_migration_spread_bp"].to_numpy()
    rate_duration = portfolio["rate_duration"].to_numpy()
    spread_duration = portfolio["spread_duration"].to_numpy()
    convexity = portfolio["convexity"].to_numpy()
    bond_rates = -value * rate_duration * d_rate * BP
    bond_spread = -value * spread_duration * d_spread * BP
    bond_migration = -value * spread_duration * d_migration * BP
    convexity_move = (np.where(is_fixed, d_rate, 0.0) + d_spread + d_migration) * BP
    bond_second_order = 0.5 * value * convexity * convexity_move**2
    loan_migration = -portfolio["ead_usd"].to_numpy() * portfolio["lgd"].to_numpy() * (shocks["pd_after"].to_numpy() - shocks["pd_before"].to_numpy())
    irs_rates = portfolio["dv01_usd_per_bp"].to_numpy() * d_rate
    equity_pnl = value * shocks["equity_return"].to_numpy()
    scale = portfolio["contracts"].to_numpy() * portfolio["multiplier"].to_numpy()
    spot_move = portfolio["underlying_price"].to_numpy() * shocks["equity_return"].to_numpy()
    option_delta = scale * portfolio["delta"].to_numpy() * spot_move
    option_gamma = 0.5 * scale * portfolio["gamma"].to_numpy() * spot_move**2
    option_vega = scale * portfolio["vega_per_vol_pt"].to_numpy() * shocks["d_vol_pts"].to_numpy()
    result = pd.DataFrame({
        "position_id": portfolio["position_id"].to_numpy(),
        "asset_class": asset,
        "rates": np.where(is_bond, bond_rates, 0.0) + np.where(is_irs, irs_rates, 0.0),
        "spread": np.where(is_bond, bond_spread, 0.0),
        "migration": np.where(is_bond, bond_migration, 0.0) + np.where(is_loan, loan_migration, 0.0),
        "equity": np.where(is_equity, equity_pnl, 0.0) + np.where(is_option, option_delta, 0.0),
        "vol": np.where(is_option, option_vega, 0.0),
        "second_order": np.where(is_bond, bond_second_order, 0.0) + np.where(is_option, option_gamma, 0.0),
    })
    result["pnl"] = result[FACTORS].sum(axis=1)
    result["value_before"] = value
    result["value_after"] = value + result["pnl"].to_numpy()
    return result


def lifetime_pd(one_year_pd: np.ndarray, years: np.ndarray) -> np.ndarray:
    return 1.0 - (1.0 - one_year_pd) ** np.maximum(years, 1.0)


def loan_lifetime_el_change(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> float:
    is_loan = (portfolio["asset_class"] == "loan").to_numpy()
    years = portfolio["maturity_years"].to_numpy()
    before = lifetime_pd(shocks["pd_before"].to_numpy(), years)
    after = lifetime_pd(shocks["pd_after"].to_numpy(), years)
    exposure = portfolio["ead_usd"].to_numpy() * portfolio["lgd"].to_numpy()
    return float(-np.sum(np.where(is_loan, exposure * (after - before), 0.0)))
