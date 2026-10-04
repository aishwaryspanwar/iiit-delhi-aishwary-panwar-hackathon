from src.riskengine.cluster import build_events
from src.riskengine.impact import baseline_mentions, cluster_components, cluster_impact, impact_components, item_impact


def components(**overrides) -> dict[str, float]:
    base = {"class_prior": 0.5, "sentiment_mag": 0.5, "entity_importance": 0.5, "cue_bonus": 0.5}
    base.update(overrides)
    return base


def test_item_impact_bounds():
    assert item_impact(components(class_prior=0, sentiment_mag=0, entity_importance=0, cue_bonus=0)) == 1.0
    assert item_impact(components(class_prior=1, sentiment_mag=1, entity_importance=1, cue_bonus=1)) == 10.0


def test_item_impact_formula():
    assert item_impact(components()) == round(1 + 9 * 0.5, 1)


def test_item_impact_monotone_in_sentiment_magnitude():
    low = item_impact(components(sentiment_mag=0.1))
    high = item_impact(components(sentiment_mag=0.9))
    assert high > low


def test_impact_components_use_absolute_sentiment():
    negative = impact_components("geopolitical", -0.8, [], "invasion")
    positive = impact_components("geopolitical", 0.8, [], "invasion")
    assert negative == positive


def test_baseline_uses_trailing_median_with_floor():
    assert baseline_mentions([]) == 2.0
    assert baseline_mentions([1, 1, 1]) == 2.0
    assert baseline_mentions([10, 30, 20]) == 20.0
    assert baseline_mentions([10, 20, 30, 40]) == 25.0


def test_cluster_components_bounds_and_values():
    quiet = cluster_components([5.5], 1, 2, 2.0)
    assert quiet == {"severity": 0.5, "breadth": 0.0, "abnormal_volume": 0.0}
    loud = cluster_components([10.0, 10.0, 10.0], 30, 200, 2.0)
    assert loud == {"severity": 1.0, "breadth": 1.0, "abnormal_volume": 1.0}
    assert cluster_impact(loud) == 10.0


def test_abnormal_volume_separates_spike_from_routine_coverage():
    routine = cluster_impact(cluster_components([9.0, 9.0, 9.0], 14, 30, 30.0))
    spike = cluster_impact(cluster_components([9.0, 9.0, 9.0], 14, 240, 30.0))
    assert spike - routine >= 2.0


def test_cluster_impact_is_monotone_in_each_component():
    base = {"severity": 0.5, "breadth": 0.5, "abnormal_volume": 0.5}
    for name in base:
        assert cluster_impact({**base, name: 0.9}) > cluster_impact(base)


def signal(signal_id: str, day: str, event_class: str, target: str, impact: float, outlets: list[str]) -> dict:
    return {
        "signal_id": signal_id, "published_at": f"{day}T10:00:00Z", "scope": "country", "scope_targets": [target],
        "event": {"class": event_class, "confidence": 0.8}, "sentiment": {"score": -0.5},
        "impact": {"score": impact}, "outlets": outlets, "sources": ["stub_news"], "duplicate_count": len(outlets) or 1,
        "cluster_id": None,
    }


def test_clusters_split_by_day_class_and_target():
    signals = [
        signal("a", "2022-02-24", "geopolitical", "country:RU", 8.0, ["reuters.com"]),
        signal("b", "2022-02-24", "geopolitical", "country:RU", 7.0, ["bbc.com"]),
        signal("c", "2022-02-24", "geopolitical", "country:CN", 6.0, ["ft.com"]),
        signal("d", "2022-02-25", "geopolitical", "country:RU", 6.0, ["ft.com"]),
    ]
    events = build_events(signals)
    assert len(events) == 3
    merged = next(e for e in events if e["n_items"] == 2)
    assert merged["n_outlets"] == 2
    assert merged["n_mentions"] == 2
    next_day = next(e for e in events if e["cluster_id"].startswith("2022-02-25"))
    assert next_day["baseline_mentions"] == 2.0
    assert all(e["warmup"] for e in events)
    assert all(s["cluster_id"] for s in signals)


def test_cluster_scope_keeps_only_consensus_targets():
    signals = [signal(str(i), "2022-02-24", "geopolitical", "country:RU", 8.0, ["reuters.com"]) for i in range(10)]
    for member in signals[:4]:
        member["scope_targets"] = ["country:RU", "country:UA"]
    signals[5]["scope_targets"] = ["country:RU", "country:PL", "sector:materials"]
    event = build_events(signals)[0]
    assert event["scope_targets"] == ["country:RU", "country:UA"]


def test_credit_event_scope_is_primary_target_only():
    signals = [signal(str(i), "2022-03-09", "credit_event", "country:RU", 8.0, ["reuters.com"]) for i in range(4)]
    for member in signals:
        member["scope_targets"] = ["country:RU", "country:UA"]
    assert build_events(signals)[0]["scope_targets"] == ["country:RU"]
