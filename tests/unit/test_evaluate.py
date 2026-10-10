import json
from pathlib import Path

import pytest

from scripts.evaluate import accuracy, classification_report, cohen_kappa, compare_windows, evaluate, macro_f1, per_class_scores, percentile

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


def test_committed_metrics_are_current():
    committed = json.loads((REPO / "data" / "eval" / "metrics.json").read_text(encoding="utf-8"))
    assert evaluate("w1") == committed


def test_committed_window_comparison_is_current():
    committed = json.loads((REPO / "data" / "eval" / "window_comparison.json").read_text(encoding="utf-8"))
    assert compare_windows() == committed


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert percentile([5.0], 0.9) == 5.0
