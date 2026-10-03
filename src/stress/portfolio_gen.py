import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.riskengine.config import DATA_DIR, load_csv, load_yaml

PORTFOLIO_PATH = DATA_DIR / "portfolio" / "portfolio_v1.csv"
COLUMNS = [
    "position_id", "asset_class", "name", "sector", "country", "rating", "ticker", "coupon_type", "direction",
    "secured", "notional_usd", "market_value_usd", "maturity_years", "ead_usd", "lgd", "rate_duration",
    "spread_duration", "convexity", "dv01_usd_per_bp", "beta", "option_type", "contracts", "multiplier",
    "underlying_price", "strike", "expiry_years", "implied_vol", "delta", "gamma", "vega_per_vol_pt",
]
SECTOR_CODES = {
    "energy": "ENR", "financials": "FIN", "utilities": "UTL", "industrials": "IND", "materials": "MAT",
    "consumer": "CON", "real_estate": "REA", "technology": "TEC", "communication": "COM", "sovereign": "SOV",
}


def par_bond_risk(maturity_years: int, annual_yield: float) -> tuple[float, float]:
    times = np.arange(1, maturity_years + 1, dtype=float)
    cashflows = np.full(maturity_years, annual_yield)
    cashflows[-1] += 1.0
    discount = (1.0 + annual_yield) ** -times
    price = float(np.sum(cashflows * discount))
    modified_duration = float(np.sum(times * cashflows * discount)) / price / (1.0 + annual_yield)
    convexity = float(np.sum(times * (times + 1.0) * cashflows * discount)) / price / (1.0 + annual_yield) ** 2
    return round(modified_duration, 4), round(convexity, 4)


def draw_musd(rng: np.random.Generator, bounds: list[float]) -> float:
    return float(round(rng.uniform(*bounds), 1) * 1e6)


def draw_years(rng: np.random.Generator, bounds: list[int]) -> int:
    return int(rng.integers(bounds[0], bounds[1] + 1))


def blank_row() -> dict:
    return {column: "" for column in COLUMNS}


def obligor_name(sector: str, country: str, counter: dict[str, int]) -> str:
    if sector == "sovereign":
        return f"Sovereign-{country}"
    key = f"{SECTOR_CODES[sector]}-{country}"
    counter[key] = counter.get(key, 0) + 1
    return f"Obligor-{key}-{counter[key]:02d}"


def loan_rows(rng: np.random.Generator, settings: dict, counter: dict[str, int]) -> list[dict]:
    rows = []
    for index, spec in enumerate(settings["loans"], start=1):
        notional = draw_musd(rng, settings["ranges"]["loan_notional_musd"])
        row = blank_row()
        row.update({
            "position_id": f"LN{index:03d}", "asset_class": "loan", "name": obligor_name(spec["sector"], spec["country"], counter),
            "sector": spec["sector"], "country": spec["country"], "rating": spec["rating"],
            "secured": str(spec["secured"]).lower(), "notional_usd": notional, "market_value_usd": notional,
            "maturity_years": draw_years(rng, settings["ranges"]["loan_maturity_years"]), "ead_usd": notional,
            "lgd": settings["lgd"]["secured" if spec["secured"] else "unsecured"],
        })
        rows.append(row)
    return rows


def bond_rows(rng: np.random.Generator, settings: dict, counter: dict[str, int]) -> list[dict]:
    rows = []
    annual_yield = settings["yield_for_convexity"]
    for index, spec in enumerate(settings["bonds"], start=1):
        notional = draw_musd(rng, settings["ranges"]["bond_notional_musd"])
        price = round(float(rng.uniform(*settings["ranges"]["bond_price_pct"])), 2)
        maturity = draw_years(rng, settings["ranges"]["bond_maturity_years"])
        duration, convexity = par_bond_risk(maturity, annual_yield)
        is_fixed = spec["coupon_type"] == "fixed"
        row = blank_row()
        row.update({
            "position_id": f"BD{index:03d}", "asset_class": "bond", "name": obligor_name(spec["sector"], spec["country"], counter),
            "sector": spec["sector"], "country": spec["country"], "rating": spec["rating"], "coupon_type": spec["coupon_type"],
            "notional_usd": notional, "market_value_usd": round(notional * price / 100.0, 2), "maturity_years": maturity,
            "rate_duration": duration if is_fixed else settings["frn_rate_duration"], "spread_duration": duration,
            "convexity": convexity,
        })
        rows.append(row)
    return rows


def irs_rows(rng: np.random.Generator, settings: dict) -> list[dict]:
    rows = []
    for index, spec in enumerate(settings["irs"], start=1):
        notional = draw_musd(rng, settings["ranges"]["irs_notional_musd"])
        maturity = draw_years(rng, settings["ranges"]["irs_maturity_years"])
        duration, _ = par_bond_risk(maturity, settings["yield_for_convexity"])
        sign = 1.0 if spec["direction"] == "payer" else -1.0
        row = blank_row()
        row.update({
            "position_id": f"SW{index:03d}", "asset_class": "irs", "name": f"USD IRS {spec['direction']} {maturity}Y",
            "sector": "rates", "country": "US", "direction": spec["direction"], "notional_usd": notional,
            "market_value_usd": round(notional * float(rng.uniform(-0.004, 0.004)), 2), "maturity_years": maturity,
            "dv01_usd_per_bp": round(sign * notional * duration * 1e-4, 2),
        })
        rows.append(row)
    return rows


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def normal_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def black_scholes(option_type: str, spot: float, strike: float, years: float, vol: float, rate: float) -> dict[str, float]:
    root = vol * math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * years) / root
    d2 = d1 - root
    discount = math.exp(-rate * years)
    if option_type == "call":
        price = spot * normal_cdf(d1) - strike * discount * normal_cdf(d2)
        delta = normal_cdf(d1)
    else:
        price = strike * discount * normal_cdf(-d2) - spot * normal_cdf(-d1)
        delta = normal_cdf(d1) - 1.0
    return {
        "price": price,
        "delta": delta,
        "gamma": normal_pdf(d1) / (spot * root),
        "vega_per_vol_pt": spot * normal_pdf(d1) * math.sqrt(years) / 100.0,
    }


def option_rows(settings: dict, equities: dict[str, dict]) -> list[dict]:
    config = settings["options"]
    rows = []
    for index, spec in enumerate(config["positions"], start=1):
        spot = config["underlying_price"]
        strike = round(spot * spec["strike_pct"], 4)
        greeks = black_scholes(spec["option_type"], spot, strike, spec["expiry_years"], spec["implied_vol"], config["risk_free_rate"])
        scale = spec["contracts"] * config["multiplier"]
        underlying = equities[spec["ticker"]]
        row = blank_row()
        row.update({
            "position_id": f"OP{index:03d}", "asset_class": "option",
            "name": f"{'Long' if spec['contracts'] > 0 else 'Short'} {spec['ticker']} {spec['option_type']} {int(spec['strike_pct'] * 100)}% {spec['expiry_years']}y",
            "sector": underlying["sector"], "country": underlying["country"], "ticker": spec["ticker"],
            "notional_usd": round(abs(scale) * spot, 2), "market_value_usd": round(scale * greeks["price"], 2),
            "beta": underlying["beta"], "option_type": spec["option_type"], "contracts": spec["contracts"],
            "multiplier": config["multiplier"], "underlying_price": spot, "strike": strike,
            "expiry_years": spec["expiry_years"], "implied_vol": spec["implied_vol"],
            "delta": round(greeks["delta"], 6), "gamma": round(greeks["gamma"], 8), "vega_per_vol_pt": round(greeks["vega_per_vol_pt"], 6),
        })
        rows.append(row)
    return rows


def equity_rows(rng: np.random.Generator, settings: dict) -> list[dict]:
    companies = load_csv("entities.csv").set_index("ticker")
    rows = []
    for index, spec in enumerate(settings["equities"], start=1):
        company = companies.loc[spec["ticker"]]
        value = draw_musd(rng, settings["ranges"]["equity_value_musd"])
        row = blank_row()
        row.update({
            "position_id": f"EQ{index:03d}", "asset_class": "equity", "name": company["name"], "sector": company["sector"],
            "country": company["country"], "ticker": spec["ticker"], "notional_usd": value, "market_value_usd": value,
            "beta": spec["beta"],
        })
        rows.append(row)
    return rows


def generate_portfolio() -> pd.DataFrame:
    settings = load_yaml("portfolio.yaml")
    rng = np.random.default_rng(settings["seed"])
    counter: dict[str, int] = {}
    loans = loan_rows(rng, settings, counter)
    bonds = bond_rows(rng, settings, counter)
    swaps = irs_rows(rng, settings)
    equities = equity_rows(rng, settings)
    options = option_rows(settings, {row["ticker"]: row for row in equities})
    rows = loans + bonds + swaps + equities + options
    return pd.DataFrame(rows, columns=COLUMNS)


def write_portfolio(frame: pd.DataFrame, path: Path = PORTFOLIO_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")


def load_portfolio(path: Path = PORTFOLIO_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    numeric = [
        "notional_usd", "market_value_usd", "maturity_years", "ead_usd", "lgd", "rate_duration", "spread_duration", "convexity",
        "dv01_usd_per_bp", "beta", "contracts", "multiplier", "underlying_price", "strike", "expiry_years", "implied_vol",
        "delta", "gamma", "vega_per_vol_pt",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column].replace("", "0")).astype(float)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PORTFOLIO_PATH)
    args = parser.parse_args()
    frame = generate_portfolio()
    write_portfolio(frame, args.output)
    print(f"wrote {len(frame)} positions to {args.output}")


if __name__ == "__main__":
    main()
