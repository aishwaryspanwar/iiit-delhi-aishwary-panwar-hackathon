import hashlib

import pytest

from src.pipeline import run_pipeline
from src.riskengine.config import PROCESSED_DIR
from src.riskengine.io import read_json, read_jsonl, validate_records
from src.stress.engine import run_stress
from src.stress.portfolio_gen import PORTFOLIO_PATH, generate_portfolio, load_portfolio, write_portfolio
from src.stress.valuation import FACTORS


def digest(path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def stub_output(tmp_path_factory):
    out = tmp_path_factory.mktemp("stub")
    run_pipeline("stub", "vader", out)
    return out


def test_all_records_schema_valid(stub_output):
    validate_records(read_jsonl(stub_output / "signals_v1.jsonl.gz"), "signal_v1")
    validate_records(read_jsonl(stub_output / "events_v1.jsonl.gz"), "event_v1")


def test_build_is_deterministic(stub_output, tmp_path):
    run_pipeline("stub", "vader", tmp_path)
    for name in ["signals_v1.jsonl.gz", "events_v1.jsonl.gz", "stress_results_v1.json"]:
        assert digest(stub_output / name) == digest(tmp_path / name)


def test_committed_stub_outputs_are_current(stub_output):
    for name in ["signals_v1.jsonl.gz", "events_v1.jsonl.gz", "stress_results_v1.json"]:
        assert digest(PROCESSED_DIR / "stub" / name) == digest(stub_output / name)


def test_portfolio_regenerates_byte_identical(tmp_path):
    regenerated_path = tmp_path / "portfolio.csv"
    write_portfolio(generate_portfolio(), regenerated_path)
    assert digest(regenerated_path) == digest(PORTFOLIO_PATH)
    assert len(load_portfolio()) == 44


def test_portfolio_has_required_asset_mix():
    portfolio = load_portfolio()
    assert {"loan", "bond", "irs", "equity", "option"} <= set(portfolio["asset_class"])
    assert (portfolio["market_value_usd"] > 0).sum() > 30


def test_stub_triggers_expected_events(stub_output):
    results = read_json(stub_output / "stress_results_v1.json")
    triggered = {r["cluster_id"] for r in results["runs"]}
    assert "2022-02-24|geopolitical|country|country:RU" in triggered
    assert "2022-03-03|credit_event|country|country:RU" in triggered
    assert not any("|product_launch|" in c for c in triggered)


def test_attribution_conserves_total(stub_output):
    results = read_json(stub_output / "stress_results_v1.json")
    for run in results["runs"]:
        totals = run["totals"]
        assert sum(run["by_factor"][f] for f in FACTORS) == pytest.approx(totals["pnl"], abs=0.05)
        assert sum(a["pnl"] for a in run["by_asset_class"]) == pytest.approx(totals["pnl"], abs=0.05)
        assert sum(p["pnl"] for p in run["positions"]) == pytest.approx(totals["pnl"], abs=0.5)
        assert totals["value_after"] == pytest.approx(totals["value_before"] + totals["pnl"], abs=0.05)


def test_geopolitical_run_hits_in_scope_russia_exposure(stub_output):
    results = read_json(stub_output / "stress_results_v1.json")
    run = next(r for r in results["runs"] if r["class"] == "geopolitical")
    in_scope = [p for p in run["positions"] if p["in_scope"]]
    assert in_scope and all(p["country"] in {"RU", "UA"} for p in in_scope)
    assert run["shocks_applied"]["rates_bp"] < 0
    assert run["totals"]["pnl"] < 0


def test_zero_multiplier_floor_respected():
    portfolio = load_portfolio()
    event = {"cluster_id": "x", "class": "macroeconomic", "impact": 7.0, "scope": "macro", "scope_targets": [], "t_start": "2022-03-16T00:00:00Z",
             "representative_signal_ids": ["none"], "confidence_mean": 1.0, "sentiment_mean": -0.5, "n_items": 1, "n_outlets": 1}
    run = run_stress(portfolio, event, {})
    assert run["shocks_applied"]["multiplier"] == 0.5
    assert run["in_scope_positions"] == 0
