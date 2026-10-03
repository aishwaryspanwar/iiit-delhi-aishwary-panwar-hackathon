from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from src.riskengine.config import load_csv, load_yaml
from src.riskengine.entities import entity_table


@dataclass(frozen=True)
class ScopeFilter:
    scope: str
    countries: frozenset[str]
    sectors: frozenset[str]
    tickers: frozenset[str]
    unlisted_names: frozenset[tuple[str, str]]


@lru_cache(maxsize=1)
def shock_config() -> dict:
    return load_yaml("shocks.yaml")


@lru_cache(maxsize=1)
def rating_table() -> pd.DataFrame:
    table = load_csv("rating_table.csv").copy()
    table["notch_index"] = table["notch_index"].astype(int)
    table["pd_1y"] = table["pd_1y"].astype(float)
    table["spread_bp"] = table["spread_bp"].astype(float)
    return table.set_index("rating")


def severity_multiplier(impact: float) -> float:
    settings = shock_config()
    threshold = settings["trigger"]["impact_threshold"]
    floor = settings["severity"]["floor_multiplier"]
    scaled = floor + (1.0 - floor) * (impact - threshold) / (10.0 - threshold)
    return round(min(1.0, max(floor, scaled)), 4)


def scope_filter(scope: str, targets: list[str]) -> ScopeFilter:
    table = entity_table()
    countries, sectors, tickers, unlisted = set(), set(), set(), set()
    for target in targets:
        row = table.get(target)
        if row is None:
            continue
        if row["type"] == "country":
            countries.add(row["country"])
        elif row["type"] in ("sector", "commodity"):
            sectors.add(row["sector"])
        elif row["type"] == "company" and row["ticker"]:
            tickers.add(row["ticker"])
        elif row["type"] == "company":
            unlisted.add((row["sector"], row["country"]))
    return ScopeFilter(scope, frozenset(countries), frozenset(sectors), frozenset(tickers), frozenset(unlisted))


def in_scope_mask(portfolio: pd.DataFrame, selection: ScopeFilter) -> np.ndarray:
    country_match = portfolio["country"].isin(selection.countries).to_numpy()
    sector_match = portfolio["sector"].isin(selection.sectors).to_numpy()
    if selection.scope == "single_name":
        ticker_match = portfolio["ticker"].isin(selection.tickers).to_numpy()
        pairs = list(zip(portfolio["sector"], portfolio["country"]))
        unlisted_match = np.array([pair in selection.unlisted_names for pair in pairs], dtype=bool)
        return ticker_match | unlisted_match
    if selection.scope == "sector":
        return sector_match & country_match if selection.countries else sector_match
    if selection.scope == "country":
        return country_match & sector_match if selection.sectors else country_match
    return np.zeros(len(portfolio), dtype=bool)


def downgraded_ratings(ratings: pd.Series, notches: np.ndarray) -> pd.Series:
    table = rating_table()
    by_index = table.reset_index().set_index("notch_index")["rating"]
    worst = int(table["notch_index"].max())
    new_index = []
    for rating, notch in zip(ratings, notches):
        if rating in table.index:
            new_index.append(by_index[min(worst, int(table.loc[rating, "notch_index"]) + int(notch))])
        else:
            new_index.append(rating)
    return pd.Series(new_index, index=ratings.index)


def position_shocks(portfolio: pd.DataFrame, event_class: str, impact: float, scope: str, targets: list[str]) -> pd.DataFrame:
    settings = shock_config()
    scenario = settings["scenarios"][event_class]
    multiplier = severity_multiplier(impact)
    table = rating_table()
    mask = in_scope_mask(portfolio, scope_filter(scope, targets))
    rated = portfolio["rating"].isin(table.index).to_numpy()
    bucket = portfolio["rating"].map(table["bucket"]).fillna("IG")
    base_spread = bucket.map(scenario["spread_bp"]).astype(float).to_numpy() * multiplier
    in_scope = scenario["in_scope"]
    max_notches = settings["severity"]["max_rating_notches"]
    notches_value = min(max_notches, abs(int(round(in_scope["rating_notches"] * multiplier))))
    notches = np.where(mask & rated, notches_value, 0)
    new_rating = downgraded_ratings(portfolio["rating"], notches)
    old_spread = portfolio["rating"].map(table["spread_bp"]).fillna(0.0).to_numpy()
    new_spread = new_rating.map(table["spread_bp"]).fillna(0.0).to_numpy()
    sector_excess = portfolio["sector"].map(scenario["sector_excess"]).fillna(0.0).astype(float).to_numpy()
    beta = portfolio["beta"].to_numpy()
    equity_return = (beta * scenario["equity_market"] + sector_excess + np.where(mask, in_scope["equity_excess"], 0.0)) * multiplier
    return pd.DataFrame({
        "position_id": portfolio["position_id"].to_numpy(),
        "in_scope": mask,
        "d_rate_bp": np.full(len(portfolio), scenario["rates_bp"] * multiplier),
        "d_spread_bp": np.where(rated, base_spread + np.where(mask, in_scope["spread_bp"] * multiplier, 0.0), 0.0),
        "rating_notches": notches,
        "rating_after": new_rating.to_numpy(),
        "d_migration_spread_bp": np.where(rated, new_spread - old_spread, 0.0),
        "pd_before": portfolio["rating"].map(table["pd_1y"]).fillna(0.0).to_numpy(),
        "pd_after": new_rating.map(table["pd_1y"]).fillna(0.0).to_numpy(),
        "equity_return": np.where(portfolio["asset_class"].isin(["equity", "option"]).to_numpy(), equity_return, 0.0),
        "d_vol_pts": np.full(len(portfolio), scenario["vol_pts"] * multiplier),
    })


def scenario_summary(event_class: str, impact: float) -> dict:
    scenario = shock_config()["scenarios"][event_class]
    multiplier = severity_multiplier(impact)
    return {
        "multiplier": multiplier,
        "equity_market": round(scenario["equity_market"] * multiplier, 4),
        "sector_excess": {k: round(v * multiplier, 4) for k, v in sorted(scenario["sector_excess"].items())},
        "rates_bp": round(scenario["rates_bp"] * multiplier, 2),
        "spread_bp": {k: round(v * multiplier, 2) for k, v in sorted(scenario["spread_bp"].items())},
        "vol_pts": round(scenario["vol_pts"] * multiplier, 2),
        "in_scope": {
            "spread_bp": round(scenario["in_scope"]["spread_bp"] * multiplier, 2),
            "rating_notches": min(shock_config()["severity"]["max_rating_notches"], abs(int(round(scenario["in_scope"]["rating_notches"] * multiplier)))),
            "equity_excess": round(scenario["in_scope"]["equity_excess"] * multiplier, 4),
        },
    }
