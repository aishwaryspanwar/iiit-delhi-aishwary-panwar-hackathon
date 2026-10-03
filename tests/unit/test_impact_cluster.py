import math

from src.riskengine.cluster import build_events
from src.riskengine.impact import breadth_term, cluster_impact, impact_components, item_impact


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


def test_breadth_zero_for_single_outlet():
    assert breadth_term(1) == 0.0
    assert breadth_term(0) == 0.0
    assert breadth_term(4) == round(0.5 * math.log(4), 4)


def test_cluster_impact_capped_at_ten():
    assert cluster_impact([9.8, 9.9], 50)[2] == 10.0


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
    assert merged["impact"] == round(min(10, 7.5 + 0.5 * math.log(2)), 1)
    assert all(s["cluster_id"] for s in signals)
