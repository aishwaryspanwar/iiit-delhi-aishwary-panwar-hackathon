import numpy as np
import pandas as pd

from src.stress.shocks import rating_table

FACTORS = ["rates", "spread", "migration", "equity", "vol", "second_order"]
BP = 1e-4
BANKING_BOOK = {"loan"}
SICR_NOTCHES = 3
DEFAULT_NOTCH = 16
CAPITAL_RATIO = 0.08


def lifetime_pd(one_year_pd: np.ndarray, years: np.ndarray) -> np.ndarray:
    return 1.0 - (1.0 - one_year_pd) ** np.maximum(years, 1.0)


def ifrs9_stages(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    table = rating_table()
    before = portfolio["rating"].map(table["notch_index"]).fillna(-1).to_numpy()
    after = shocks["rating_after"].map(table["notch_index"]).fillna(-1).to_numpy()
    crossed = (before <= table.loc["BBB-", "notch_index"]) & (after > table.loc["BBB-", "notch_index"])
    stage_after = np.where(after >= DEFAULT_NOTCH, 3, np.where((after - before >= SICR_NOTCHES) | crossed, 2, 1))
    return np.ones(len(portfolio), dtype=int), stage_after


def expected_credit_loss(exposure: np.ndarray, pd_1y: np.ndarray, years: np.ndarray, stage: np.ndarray) -> np.ndarray:
    lifetime = lifetime_pd(pd_1y, years)
    probability = np.where(stage == 3, 1.0, np.where(stage == 2, lifetime, pd_1y))
    return exposure * probability


def ifrs9_view(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> pd.DataFrame:
    exposure = portfolio["ead_usd"].to_numpy() * portfolio["lgd"].to_numpy()
    years = portfolio["maturity_years"].to_numpy()
    stage_before, stage_after = ifrs9_stages(portfolio, shocks)
    ecl_before = expected_credit_loss(exposure, shocks["pd_before"].to_numpy(), years, stage_before)
    ecl_after = expected_credit_loss(exposure, shocks["pd_after"].to_numpy(), years, stage_after)
    is_loan = (portfolio["asset_class"] == "loan").to_numpy()
    return pd.DataFrame({
        "position_id": portfolio["position_id"].to_numpy(),
        "stage_before": np.where(is_loan, stage_before, 0),
        "stage_after": np.where(is_loan, stage_after, 0),
        "ecl_before": np.where(is_loan, ecl_before, 0.0),
        "ecl_after": np.where(is_loan, ecl_after, 0.0),
    })


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
    credit = ifrs9_view(portfolio, shocks)
    loan_provision = -(credit["ecl_after"].to_numpy() - credit["ecl_before"].to_numpy())
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
        "migration": np.where(is_bond, bond_migration, 0.0) + np.where(is_loan, loan_provision, 0.0),
        "equity": np.where(is_equity, equity_pnl, 0.0) + np.where(is_option, option_delta, 0.0),
        "vol": np.where(is_option, option_vega, 0.0),
        "second_order": np.where(is_bond, bond_second_order, 0.0) + np.where(is_option, option_gamma, 0.0),
    })
    result["pnl"] = result[FACTORS].sum(axis=1)
    result["value_before"] = value
    result["value_after"] = value + result["pnl"].to_numpy()
    result["book"] = np.where(np.isin(asset, list(BANKING_BOOK)), "banking", "fair_value")
    result["stage_before"] = credit["stage_before"].to_numpy()
    result["stage_after"] = credit["stage_after"].to_numpy()
    return result


def loan_lifetime_el_change(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> float:
    is_loan = (portfolio["asset_class"] == "loan").to_numpy()
    years = portfolio["maturity_years"].to_numpy()
    before = lifetime_pd(shocks["pd_before"].to_numpy(), years)
    after = lifetime_pd(shocks["pd_after"].to_numpy(), years)
    exposure = portfolio["ead_usd"].to_numpy() * portfolio["lgd"].to_numpy()
    return float(-np.sum(np.where(is_loan, exposure * (after - before), 0.0)))


def loan_one_year_el_change(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> float:
    is_loan = (portfolio["asset_class"] == "loan").to_numpy()
    exposure = portfolio["ead_usd"].to_numpy() * portfolio["lgd"].to_numpy()
    return float(-np.sum(np.where(is_loan, exposure * (shocks["pd_after"].to_numpy() - shocks["pd_before"].to_numpy()), 0.0)))


def loan_fair_value_change(portfolio: pd.DataFrame, shocks: pd.DataFrame, annual_yield: float = 0.04) -> float:
    is_loan = (portfolio["asset_class"] == "loan").to_numpy()
    years = np.maximum(portfolio["maturity_years"].to_numpy(), 1.0)
    duration = (1.0 - (1.0 + annual_yield) ** -years) / annual_yield
    move = (shocks["d_spread_bp"].to_numpy() + shocks["d_migration_spread_bp"].to_numpy()) * BP
    return float(-np.sum(np.where(is_loan, portfolio["ead_usd"].to_numpy() * duration * move, 0.0)))


def risk_weights(portfolio: pd.DataFrame, ratings: pd.Series) -> np.ndarray:
    table = rating_table()
    sovereign = (portfolio["sector"] == "sovereign").to_numpy()
    corporate = ratings.map(table["rw_corporate"]).fillna(1.0).to_numpy()
    sovereign_rw = ratings.map(table["rw_sovereign"]).fillna(1.0).to_numpy()
    return np.where(sovereign, sovereign_rw, corporate)


def capital_view(portfolio: pd.DataFrame, shocks: pd.DataFrame) -> dict:
    credit = portfolio["asset_class"].isin(["loan", "bond"]).to_numpy()
    exposure = np.where(portfolio["asset_class"] == "loan", portfolio["ead_usd"], portfolio["market_value_usd"]).astype(float)
    before = np.where(credit, exposure * risk_weights(portfolio, portfolio["rating"]), 0.0)
    after = np.where(credit, exposure * risk_weights(portfolio, shocks["rating_after"]), 0.0)
    return {
        "rwa_before": float(before.sum()),
        "rwa_after": float(after.sum()),
        "rwa_change": float(after.sum() - before.sum()),
        "capital_requirement_change": float(CAPITAL_RATIO * (after.sum() - before.sum())),
        "capital_ratio": CAPITAL_RATIO,
    }
