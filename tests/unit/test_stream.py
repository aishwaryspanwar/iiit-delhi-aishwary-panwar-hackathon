from datetime import datetime, timedelta, timezone

from src.stream.engine import run_stream

START = datetime(2022, 2, 1, tzinfo=timezone.utc)


def make_signal(index: int, at: datetime, event_class: str = "geopolitical", target: str = "country:RU", impact: float = 8.5,
                outlet: str | None = None, direction: str = "neutral", sentiment: float = -0.6) -> dict:
    return {
        "signal_id": f"s{index:05d}", "source": "gdelt_gkg", "published_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "country", "scope_targets": [target],
        "event": {"class": event_class, "confidence": 0.9, "direction": direction},
        "sentiment": {"score": sentiment}, "impact": {"score": impact},
        "outlets": [outlet or f"outlet{index % 12}.com"], "sources": ["gdelt_gkg"], "duplicate_count": 1, "cluster_id": None,
    }


def routine_then_spike(spike_day: int = 10, routine_per_day: int = 1, spike_items: int = 30) -> list[dict]:
    signals, index = [], 0
    for day in range(spike_day):
        for item in range(routine_per_day):
            signals.append(make_signal(index, START + timedelta(days=day, hours=12 + item), impact=6.0))
            index += 1
    for item in range(spike_items):
        signals.append(make_signal(index, START + timedelta(days=spike_day, hours=3 + item // 6)))
        index += 1
    return signals


def test_spike_after_quiet_history_triggers_an_alert_with_lead_time():
    result = run_stream(routine_then_spike())
    assert len(result.alerts) == 1
    alert = result.alerts[0]
    assert alert["detected_at"] < alert["day_end_at"]
    assert alert["first_headline_at"] <= alert["detected_at"]


def test_no_look_ahead_future_items_do_not_change_earlier_alerts():
    signals = routine_then_spike()
    early = run_stream([dict(s) for s in signals]).alerts
    later = signals + [make_signal(90000 + i, START + timedelta(days=14, hours=i % 24)) for i in range(40)]
    extended = [a for a in run_stream([dict(s) for s in later]).alerts if a["detected_at"] <= early[-1]["detected_at"]]
    assert extended == early


def test_missing_days_count_as_zero_in_the_baseline():
    signals, index = [], 0
    for day in (1, 2, 3, 8):
        for hour in range(20):
            signals.append(make_signal(index, START + timedelta(days=day, hours=hour)))
            index += 1
    events = {e["cluster_id"][:10]: e for e in run_stream(signals).events}
    assert events["2022-02-09"]["window"]["baseline_mentions"] == 8.0
    assert events["2022-02-04"]["window"]["baseline_mentions"] > 8.0


def test_warmup_blocks_alerts_in_first_days():
    signals = [make_signal(i, START + timedelta(hours=1 + i // 6)) for i in range(60)]
    result = run_stream(signals)
    assert result.alerts == []
    assert all("baseline_ready" in d["failed"] for d in result.decisions if not d["triggered"])


def test_thin_cluster_is_blocked_by_min_mentions():
    signals = routine_then_spike(spike_items=3)
    result = run_stream(signals)
    assert result.alerts == []


def test_positive_credit_action_does_not_trigger():
    signals = routine_then_spike()
    for signal in signals:
        signal["event"]["class"] = "credit_event"
        signal["event"]["direction"] = "positive"
    result = run_stream(signals)
    assert result.alerts == []
    assert any("direction_ok" in d["failed"] for d in result.decisions)


def test_cooldown_is_per_target_so_a_second_country_still_fires():
    signals = routine_then_spike()
    second = routine_then_spike()
    for signal in second:
        signal["signal_id"] = "t" + signal["signal_id"]
        signal["scope_targets"] = ["country:TW"]
    result = run_stream(signals + second)
    assert {a["scope_targets"][0] for a in result.alerts} == {"country:RU", "country:TW"}


def test_events_and_decisions_align():
    result = run_stream(routine_then_spike())
    assert [e["cluster_id"] for e in result.events] == [d["cluster_id"] for d in result.decisions]
    triggered = [d for d in result.decisions if d["triggered"]]
    assert [d["cluster_id"] for d in triggered] == [a["cluster_id"] for a in result.alerts]
    event = next(e for e in result.events if e["cluster_id"] == triggered[0]["cluster_id"])
    assert event["detected_at"] == result.alerts[0]["detected_at"]
    assert event["impact"] >= result.alerts[0]["impact"]
