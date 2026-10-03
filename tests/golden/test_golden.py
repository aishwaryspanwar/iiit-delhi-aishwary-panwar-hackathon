import json
from pathlib import Path

import pytest

from tests.golden.regenerate import compute_all

EXPECTED = json.loads((Path(__file__).resolve().parent / "expected.json").read_text(encoding="utf-8"))
ACTUAL = compute_all()


@pytest.mark.parametrize("scenario", sorted(EXPECTED))
def test_golden_scenario_matches(scenario):
    expected, actual = EXPECTED[scenario], ACTUAL[scenario]
    assert actual["multiplier"] == expected["multiplier"]
    assert actual["in_scope_positions"] == expected["in_scope_positions"]
    assert actual["total_pnl"] == pytest.approx(expected["total_pnl"], abs=1.0)
    for asset, value in expected["by_asset_class"].items():
        assert actual["by_asset_class"][asset] == pytest.approx(value, abs=1.0)
    for factor, value in expected["by_factor"].items():
        assert actual["by_factor"][factor] == pytest.approx(value, abs=1.0)
    for view, value in expected["loan_loss_views"].items():
        assert actual["loan_loss_views"][view] == pytest.approx(value, abs=1.0)


@pytest.mark.parametrize("scenario", sorted(EXPECTED))
def test_golden_scenario_attribution_conserves(scenario):
    actual = ACTUAL[scenario]
    assert sum(actual["by_factor"].values()) == pytest.approx(actual["total_pnl"], abs=0.1)
    assert sum(actual["by_asset_class"].values()) == pytest.approx(actual["total_pnl"], abs=0.1)


def test_golden_directional_expectations():
    geo, fed = ACTUAL["golden-geo-russia"], ACTUAL["golden-macro-fed"]
    assert geo["by_factor"]["rates"] > 0
    assert geo["by_asset_class"]["option"] > 0
    assert geo["loan_loss_views"]["lifetime_el_change"] < geo["loan_loss_views"]["one_year_el_change"] < 0
    assert fed["by_factor"]["rates"] < 0
    assert fed["by_asset_class"]["irs"] > 0
    assert fed["in_scope_positions"] == []
