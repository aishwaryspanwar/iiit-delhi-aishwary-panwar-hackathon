import json
from pathlib import Path

import pytest

from scripts.evaluate import accuracy, bootstrap_interval, classification_report, cohen_kappa, compare_windows, evaluate, macro_f1, naive_keyword_class, per_class_scores, percentile, spearman
from src.riskengine.config import config_hash

REPO = Path(__file__).resolve().parents[2]


def test_accuracy_and_macro_f1_on_toy_data():
    truth = ["a", "a", "b", "b"]
    predicted = ["a", "b", "b", "b"]
    assert accuracy(truth, predicted) == 0.75
    scores = per_class_scores(truth, predicted, ["a", "b"])
    assert scores["a"] == {"precision": 1.0, "recall": 0.5, "f1": 0.6667, "support": 2}
    assert scores["b"]["f1"] == 0.8
    assert macro_f1(truth, predicted, ["a", "b", "c"]) == pytest.approx((0.6667 + 0.8) / 2)


def test_macro_f1_ignores_labels_absent_from_truth():
    assert macro_f1(["a", "a"], ["a", "a"], ["a", "b"]) == 1.0


def test_cohen_kappa_known_values():
    assert cohen_kappa(["x", "y", "x", "y"], ["x", "y", "x", "y"]) == 1.0
    assert cohen_kappa(["x", "x", "y", "y"], ["x", "y", "x", "y"]) == 0.0
    assert cohen_kappa(["x", "x"], ["x", "x"]) == 1.0


def test_majority_baseline():
    report = classification_report(["n", "n", "n", "p"], ["p", "p", "n", "p"], ["n", "p"])
    assert report["majority_label"] == "n"
    assert report["majority_accuracy"] == 0.75
    assert report["accuracy"] == 0.5


COMMITTED = json.loads((REPO / "data" / "eval" / "metrics.json").read_text(encoding="utf-8"))


def test_committed_metrics_are_current():
    assert evaluate() == COMMITTED


def test_metrics_record_the_current_config():
    assert COMMITTED["config_hash"] == config_hash()


@pytest.mark.parametrize("split", ["w1_test", "w3_test"])
def test_claim_event_classes_beat_the_majority_baseline(split):
    report = COMMITTED["splits"][split]["representative"]
    lower_bound = report["event_class"]["macro_f1_ci95"][0]
    assert lower_bound > report["event_class"]["majority_macro_f1"]


@pytest.mark.parametrize("split", ["w1_test", "w3_test"])
def test_claim_sentiment_beats_the_majority_baseline_on_macro_f1(split):
    report = COMMITTED["splits"][split]["representative"]
    assert report["sentiment_finbert"]["macro_f1_ci95"][0] > report["sentiment_finbert"]["majority_macro_f1"]


def test_claim_engine_alerts_beat_the_base_rate_in_shock_windows():
    for window in ("w1", "w3"):
        quality = COMMITTED["trigger_quality"][window]
        assert quality["engine_alerts"]["precision"] > quality["base_rate"]


def test_committed_results_page_is_current():
    from scripts.render_results import RESULTS_PATH, render

    assert RESULTS_PATH.read_text(encoding="utf-8") == render()


def test_spearman_and_bootstrap_helpers():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    interval = bootstrap_interval(["a", "b", "a", "b"], ["a", "b", "a", "a"], accuracy)
    assert 0.0 <= interval[0] <= interval[1] <= 1.0


def test_naive_keyword_baseline():
    assert naive_keyword_class("Oil prices jump") == "commodity_energy"
    assert naive_keyword_class("Team wins final") == "other"


def test_committed_window_comparison_is_current():
    committed = json.loads((REPO / "data" / "eval" / "window_comparison.json").read_text(encoding="utf-8"))
    assert compare_windows() == committed


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert percentile([5.0], 0.9) == 5.0
