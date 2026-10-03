import pytest

from src.stress.trigger import evaluate_triggers


def event(cluster_id: str, t_start: str, impact: float = 8.5, event_class: str = "geopolitical", confidence: float = 0.8, sentiment: float = -0.5, target: str = "country:RU", outlets: int = 3) -> dict:
    return {
        "cluster_id": cluster_id, "t_start": t_start, "impact": impact, "class": event_class,
        "confidence_mean": confidence, "sentiment_mean": sentiment, "scope_targets": [target], "n_outlets": outlets,
    }


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({}, []),
        ({"impact": 7.0}, ["impact_above_threshold"]),
        ({"event_class": "product_launch"}, ["stress_class"]),
        ({"confidence": 0.5}, ["confidence_ok"]),
        ({"sentiment": 0.4}, ["not_positive"]),
        ({"outlets": 1}, ["corroborated"]),
        ({"outlets": 0}, ["corroborated"]),
    ],
)
def test_trigger_conditions(overrides, failed):
    decision = evaluate_triggers([event("x", "2022-02-24T03:00:00Z", **overrides)])[0]
    assert decision["failed"] == failed
    assert decision["triggered"] is (not failed)


def test_cooldown_blocks_repeat_within_window():
    decisions = evaluate_triggers([event("a", "2022-02-24T03:00:00Z"), event("b", "2022-02-25T03:00:00Z")])
    assert [d["triggered"] for d in decisions] == [True, False]
    assert decisions[1]["failed"] == ["cooldown"]


def test_cooldown_rearms_on_higher_impact_or_after_window():
    escalated = evaluate_triggers([event("a", "2022-02-24T03:00:00Z", impact=7.5), event("b", "2022-02-25T03:00:00Z", impact=8.6)])
    assert [d["triggered"] for d in escalated] == [True, True]
    later = evaluate_triggers([event("a", "2022-02-24T03:00:00Z"), event("b", "2022-02-28T03:00:00Z")])
    assert [d["triggered"] for d in later] == [True, True]


def test_cooldown_is_per_class_and_target():
    decisions = evaluate_triggers([event("a", "2022-02-24T03:00:00Z"), event("b", "2022-02-24T04:00:00Z", target="country:CN")])
    assert [d["triggered"] for d in decisions] == [True, True]
