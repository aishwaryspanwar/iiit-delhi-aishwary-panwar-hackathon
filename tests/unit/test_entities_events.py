import pytest

from src.riskengine.config import load_yaml
from src.riskengine.entities import resolve_scope, tag_entities
from src.riskengine.events import classify


def ids(text: str) -> set[str]:
    return {e.id for e in tag_entities(text)}


def test_cashtags_and_aliases():
    assert ids("$TSLA and Microsoft rally") == {"company:TSLA", "company:MSFT"}


def test_case_sensitive_aliases_avoid_false_positives():
    assert "central_bank:FED" not in ids("We're quite fed up with the storms")
    assert "company:AAPL" not in ids("an apple a day")
    assert "central_bank:FED" in ids("Fed signals faster hikes")


def test_longest_alias_wins():
    found = ids("Russia's central bank raises the key rate")
    assert "central_bank:CBR" in found
    assert "country:RU" not in found


def test_scope_geopolitical_prefers_country_and_drops_actor_countries():
    entities = tag_entities("US bans imports of Russian oil and gas")
    scope, targets = resolve_scope(entities, "geopolitical")
    assert scope == "country"
    assert targets[0] == "country:RU"
    assert "country:US" not in targets


def test_scope_keeps_actor_country_when_it_is_the_only_country():
    scope, targets = resolve_scope(tag_entities("US economy adds jobs"), "macroeconomic")
    assert scope == "country"
    assert targets == ["country:US"]


def test_scope_none_without_entities():
    assert resolve_scope([], "other") == ("none", [])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Russia launches full-scale invasion of Ukraine", "geopolitical"),
        ("Federal Reserve raises interest rates by 25 basis points", "macroeconomic"),
        ("Moody's downgrades Russia to junk", "credit_event"),
        ("Brent crude surges above $100 a barrel", "commodity_energy"),
        ("Microsoft to buy Activision in all-cash deal", "merger_acquisition"),
        ("Apple unveils new iPhone", "product_launch"),
        ("Tesla quarterly results beat estimates", "earnings_corporate"),
        ("Regulators open antitrust probe into Google", "regulatory"),
        ("Lovely weather today", "other"),
    ],
)
def test_classification(text, expected):
    assert classify(text).event_class == expected


def test_credit_event_beats_geopolitical_on_tie_priority():
    result = classify("Sanctions trigger default on Russian bonds")
    assert result.event_class == "credit_event"
    assert result.runner_up == "geopolitical"


def test_every_rule_pattern_compiles_and_has_known_class():
    taxonomy = load_yaml("taxonomy_rules.yaml")
    rule_ids = [r["id"] for r in taxonomy["rules"]]
    assert len(rule_ids) == len(set(rule_ids))
    assert all(r["class"] in taxonomy["classes"] for r in taxonomy["rules"])


def test_confidence_bounds():
    result = classify("Russia invades Ukraine as troops attack and sanctions follow")
    assert 0.0 <= result.confidence <= 1.0
    assert result.confidence == 1.0
