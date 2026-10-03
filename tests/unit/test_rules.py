import pytest

from src.riskengine.config import load_yaml
from src.riskengine.events import classify

POSITIVE_EXAMPLES = {
    "GEO-001": "Russia launches invasion of Ukraine",
    "GEO-002": "EU agrees new sanctions on Moscow",
    "GEO-003": "Troops mass near the border as war fears grow",
    "GEO-004": "NATO allies hold talks as tensions rise",
    "GEO-005": "Banks cut off from SWIFT as oligarchs face asset freezes",
    "GEO-006": "Street fighting begins in Kyiv as siege tightens",
    "MAC-001": "Fed raises interest rates by 25 basis points",
    "MAC-002": "US CPI inflation hits a 40-year high",
    "MAC-003": "Economists warn of recession as GDP slows",
    "MAC-004": "Treasury yields climb as the yield curve flattens",
    "MAC-005": "Rouble plunges as capital controls are imposed",
    "CRD-001": "Russia averts default with dollar payment",
    "CRD-002": "Agency downgrades Russia to junk status",
    "CRD-003": "Retailer files for Chapter 11 bankruptcy protection",
    "CRD-004": "Credit default swaps on Russian debt surge",
    "CRD-005": "Fitch places sovereign on watch",
    "COM-001": "Brent crude jumps above $110 as gas prices soar",
    "COM-002": "Wheat and nickel hit record highs",
    "COM-003": "OPEC+ sticks to plan despite energy crisis",
    "REG-001": "Antitrust regulators open a probe into Google ad business",
    "REG-002": "Company sued as new rules take effect",
    "MNA-001": "Microsoft agrees to buy Activision in all-cash deal",
    "MNA-002": "Investor takes stake in miner via tender offer",
    "ERN-001": "Tesla quarterly results beat estimates on revenue",
    "ERN-002": "Retailer announces buyback and new CEO",
    "ERN-003": "Bank raises price target on Apple shares",
    "PRD-001": "Apple unveils new iPhone at spring event",
}

CREDIT_PHRASINGS = [
    "Russia's Credit Rating Cut to 'Junk' by Moody's, Fitch Due to Sanctions",
    "Russia cut to 'junk' by Moody's, Fitch; tanks roll into Kherson",
    "S&P downgrades several Russia banks, places others on CreditWatch negative",
    "Fitch slashes Russian debt further into junk, says default imminent",
]

FALSE_POSITIVE_GUARDS = [
    ("By default the app opens in dark mode", "credit_event"),
    ("Analyst downgrades Alibaba to sell", "credit_event"),
    ("Fasano adds Brazilian glamour to fine dining scene", "regulatory"),
    ("3 top tech stocks to buy in February", "merger_acquisition"),
    ("West Belfast murder investigation after stabbing", "regulatory"),
]


def test_every_rule_has_a_positive_example():
    rule_ids = {rule["id"] for rule in load_yaml("taxonomy_rules.yaml")["rules"]}
    assert rule_ids == set(POSITIVE_EXAMPLES)


@pytest.mark.parametrize(("rule_id", "text"), sorted(POSITIVE_EXAMPLES.items()))
def test_rule_fires_on_its_example(rule_id, text):
    result = classify(text)
    rule_class = next(r["class"] for r in load_yaml("taxonomy_rules.yaml")["rules"] if r["id"] == rule_id)
    assert result.event_class == rule_class
    assert rule_id in result.matched_rules


@pytest.mark.parametrize(("text", "wrong_class"), FALSE_POSITIVE_GUARDS)
def test_known_false_positives_are_avoided(text, wrong_class):
    assert classify(text).event_class != wrong_class


@pytest.mark.parametrize("text", CREDIT_PHRASINGS)
def test_credit_rating_actions_in_any_word_order(text):
    assert classify(text).event_class == "credit_event"
