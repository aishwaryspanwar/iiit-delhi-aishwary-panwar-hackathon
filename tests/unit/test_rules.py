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
    "CRD-005": "Fitch warns of wider credit spreads",
    "CRD-006": "Moody's upgrades senior unsecured rating of CNH Industrial from Baa3 to Baa2",
    "GEO-007": "China pledges aid to Ukraine",
    "MAC-006": "Fed's forecasts clouded by fog of war",
    "REG-003": "Shareholders file lawsuit against the regulator",
    "REG-004": "Law firm investigates the merger and encourages investors to contact the firm",
    "ERN-004": "Why DigitalOcean Stock Soared More Than 20% This Week",
    "ERN-005": "Web Werks to set up data centres in Chennai",
    "PRD-002": "Siri gets a new voice in the beta version of iOS 15.4",
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
    "REG-005": "PM Modi bans Tesla in India",
    "REG-006": "FDA approves Eli Lilly's Alzheimer's drug",
    "REG-007": "China blocks Intel's acquisition of Tower Semiconductor",
    "ERN-006": "Microsoft beats estimates as cloud revenue surges",
    "ERN-007": "Nvidia misses revenue expectations, shares tumble",
    "GEO-008": "Military coup in Niger as soldiers seize power",
    "GEO-009": "Ukraine and Russia agree to a ceasefire",
    "COM-004": "Drought and crop failure push up wheat prices",
    "CRD-007": "Evergrande misses bond payment, liquidity crisis deepens",
    "MAC-007": "Rupee devaluation sparks currency crisis fears",
    "MAC-008": "RBI cuts interest rates as inflation cools",
}

DIRECTION_EXAMPLES = [
    ("PM Modi bans Tesla in India", "regulatory", "negative"),
    ("India lifts ban on Chinese apps", "regulatory", "positive"),
    ("SEBI fines Adani group firm over disclosure lapses", "regulatory", "negative"),
    ("US slaps 25% tariffs on Chinese electric vehicles", "regulatory", "negative"),
    ("Tesla recalls 2 million vehicles over autopilot defect", "regulatory", "negative"),
    ("Apple shares soar after record quarterly profit", "earnings_corporate", "positive"),
    ("Tata Motors cuts full-year guidance as JLR sales slump", "earnings_corporate", "negative"),
    ("Byju's CEO resigns amid accounting irregularities", "earnings_corporate", "negative"),
    ("Israel and Hamas agree to a truce", "geopolitical", "positive"),
    ("Credit Suisse rescue: UBS agrees bailout as bank run fears spread", "credit_event", "negative"),
]

NOT_POSITIVE = [
    "India calls for immediate de-escalation after Russian attack on Ukraine",
    "Ceasefire talks collapse as shelling resumes in Kyiv",
    "Fed rules out rate cuts this year",
]

NOT_POLICY = [
    "Reliance Jio announces new tariff plans",
    "Two-match ban for Kohli after on-field clash",
    "Riot Platforms shares rise with bitcoin",
]

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
    ("Russia launches full-scale invasion of Ukraine", "product_launch"),
    ("EU unveils new sanctions package against Moscow", "product_launch"),
    ("Normally Faze shuts down early aggression and sets the pace for the match", "geopolitical"),
    ("Payments resume May 2: Are you at risk of defaulting on student loans?", "credit_event"),
    ("Intel Has Fallen 30% Since This Analyst Cut His Rating. He Just Upgraded the Stock.", "credit_event"),
    ("Risk of recession 'uncomfortably high': Moody's Analytics chief economist", "credit_event"),
    ("Federal jury awards $85 million to California family in wrongful death lawsuit", "regulatory"),
    ("Mask violations: TSA issued hundreds of thousands of dollars in fines", "regulatory"),
    ("Ex-officer who shot and killed unarmed US teen convicted of negligent homicide", "geopolitical"),
    ("Ukraine's bid for fast-track membership of EU likely to end in disappointment", "merger_acquisition"),
    ("NIRI presents a discussion with Andy Fastow, former CFO of Enron", "earnings_corporate"),
    ("My wife loves her new Model X Plaid!", "product_launch"),
]

EXPECTED_CLASSES = [
    ("Employers add 475,000 jobs in February: ADP", "macroeconomic"),
    ("Germany, Britain and Italy Hit by Surge in Pump Prices", "commodity_energy"),
    ("Philadelphia Fed's manufacturing gauge softens in February", "macroeconomic"),
    ("Ruble 'destroyed' as Russia slides towards default", "credit_event"),
    ("JPM cuts Indian shares to 'underweight', trims target for MSCI EM index", "earnings_corporate"),
    ("Trend Micro Announces Record-Setting Results for Q4 and Fiscal Year 2021", "earnings_corporate"),
    ("UN peacekeeping mission in South Sudan extended for a year", "geopolitical"),
]

DIRECTIONS = [
    ("Fitch slashes Russian debt further into junk, says default imminent", "negative"),
    ("Moody's upgrades senior unsecured rating of CNH Industrial from Baa3 to Baa2", "positive"),
    ("S&P revises outlook on Indonesia to positive outlook", "positive"),
    ("Fed raises interest rates by 25 basis points", "neutral"),
]


def test_military_launch_is_not_a_product_launch_signal():
    result = classify("Russia launches full-scale invasion of Ukraine as explosions heard in Kyiv")
    assert result.event_class == "geopolitical"
    assert "PRD-001" not in result.matched_rules
    assert result.confidence == 1.0


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


@pytest.mark.parametrize(("text", "expected"), EXPECTED_CLASSES)
def test_review_misses_are_classified(text, expected):
    assert classify(text).event_class == expected


@pytest.mark.parametrize(("text", "direction"), DIRECTIONS)
def test_event_direction(text, direction):
    assert classify(text).direction == direction


def test_sports_context_overrides_rules():
    result = classify("TSM are your world champions after a tense grand final attack")
    assert result.event_class == "other"
    assert result.matched_rules == ("CTX-EXCLUDE",)


@pytest.mark.parametrize("text,event_class,direction", DIRECTION_EXAMPLES)
def test_policy_and_corporate_events_carry_direction(text, event_class, direction):
    result = classify(text)
    assert (result.event_class, result.direction) == (event_class, direction)


@pytest.mark.parametrize("text", NOT_POLICY)
def test_everyday_uses_of_policy_words_are_not_stress_events(text):
    assert classify(text).event_class not in ("regulatory", "geopolitical")


@pytest.mark.parametrize("text", NOT_POSITIVE)
def test_relief_words_in_a_hostile_or_negated_context_are_not_positive(text):
    assert classify(text).direction != "positive"
