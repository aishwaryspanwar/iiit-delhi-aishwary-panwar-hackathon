from datetime import datetime, timedelta, timezone

import pytest

from src.stress.shocks import shock_config
from src.stress.trigger import CHECK_LABELS, CooldownTracker, condition_checks, cooldown_key

START = datetime(2022, 2, 24, 3, tzinfo=timezone.utc)


def state(**overrides) -> dict:
    base = {
        "class": "geopolitical", "impact": 8.5, "confidence_mean": 0.8, "sentiment_mean": -0.5,
        "positive_share": 0.0, "n_outlets": 3, "n_mentions_est": 40.0, "warmup": False,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({}, []),
        ({"impact": 7.0}, ["impact_above_threshold"]),
        ({"class": "product_launch"}, ["stress_class"]),
        ({"confidence_mean": 0.5}, ["confidence_ok"]),
        ({"sentiment_mean": 0.4}, ["not_positive"]),
        ({"positive_share": 0.8}, ["direction_ok"]),
        ({"n_outlets": 1}, ["corroborated"]),
        ({"n_mentions_est": 6.0}, ["enough_mentions"]),
        ({"warmup": True}, ["baseline_ready"]),
    ],
)
def test_trigger_conditions(overrides, failed):
    checks = condition_checks(state(**overrides), shock_config()["trigger"])
    assert [name for name, passed in checks.items() if not passed] == failed


def test_every_check_has_a_label():
    assert set(condition_checks(state(), shock_config()["trigger"])) | {"cooldown"} == set(CHECK_LABELS)


def test_cooldown_blocks_repeat_within_window_and_rearms():
    tracker = CooldownTracker(hours=72, rearm_delta=1.0)
    key = cooldown_key("geopolitical", ["country:RU"])
    tracker.fire(key, START, 7.5)
    assert not tracker.allows(key, START + timedelta(hours=24), 8.0)
    assert tracker.allows(key, START + timedelta(hours=24), 8.5)
    assert tracker.allows(key, START + timedelta(hours=73), 7.1)


def test_cooldown_is_per_class_and_target():
    tracker = CooldownTracker(hours=72, rearm_delta=1.0)
    tracker.fire(cooldown_key("geopolitical", ["country:RU"]), START, 8.5)
    assert tracker.allows(cooldown_key("geopolitical", ["country:TW"]), START + timedelta(hours=1), 7.5)
    assert tracker.allows(cooldown_key("credit_event", ["country:RU"]), START + timedelta(hours=1), 7.5)
    assert not tracker.allows(cooldown_key("geopolitical", ["country:RU", "country:UA"]), START + timedelta(hours=1), 8.6)
