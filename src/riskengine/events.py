import re
from dataclasses import dataclass
from functools import lru_cache

from src.riskengine.config import load_yaml
from src.riskengine.models import EventResult

DIRECTIONS = ("negative", "positive", "neutral")


@dataclass(frozen=True)
class Rule:
    rule_id: str
    event_class: str
    weight: float
    patterns: tuple[re.Pattern[str], ...]
    excludes: tuple[re.Pattern[str], ...]
    direction: str


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    return load_yaml("taxonomy_rules.yaml")


def compile_all(patterns: list[str]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


@lru_cache(maxsize=1)
def compiled_rules() -> tuple[Rule, ...]:
    return tuple(
        Rule(
            rule_id=rule["id"],
            event_class=rule["class"],
            weight=float(rule["weight"]),
            patterns=compile_all(rule["patterns"]),
            excludes=compile_all(rule.get("exclude_patterns", [])),
            direction=rule.get("direction", "neutral"),
        )
        for rule in taxonomy()["rules"]
    )


@lru_cache(maxsize=1)
def context_excludes() -> tuple[re.Pattern[str], ...]:
    return compile_all(taxonomy().get("context_excludes", []))


def class_display_name(event_class: str) -> str:
    return taxonomy()["classes"][event_class]


def rule_matches(rule: Rule, text: str) -> bool:
    return any(p.search(text) for p in rule.patterns) and not any(p.search(text) for p in rule.excludes)


def event_direction(rules: list[Rule]) -> str:
    directions = {rule.direction for rule in rules}
    if "negative" in directions:
        return "negative"
    if "positive" in directions:
        return "positive"
    return "neutral"


def classify(text: str) -> EventResult:
    settings = taxonomy()
    if any(p.search(text) for p in context_excludes()):
        return EventResult(event_class="other", confidence=0.0, matched_rules=("CTX-EXCLUDE",), runner_up=None, direction="neutral")
    scores: dict[str, float] = {}
    matched: dict[str, list[Rule]] = {}
    for rule in compiled_rules():
        if rule_matches(rule, text):
            scores[rule.event_class] = scores.get(rule.event_class, 0.0) + rule.weight
            matched.setdefault(rule.event_class, []).append(rule)
    priority = {name: index for index, name in enumerate(settings["priority"])}
    ranked = sorted(scores.items(), key=lambda item: (-item[1], priority[item[0]]))
    if not ranked or ranked[0][1] < settings["min_score"]:
        all_rules = tuple(sorted(r.rule_id for rules in matched.values() for r in rules))
        return EventResult(event_class="other", confidence=0.0, matched_rules=all_rules, runner_up=ranked[0][0] if ranked else None, direction="neutral")
    top_class, top_score = ranked[0]
    share = top_score / sum(scores.values())
    strength = min(1.0, top_score / settings["confidence_saturation"])
    return EventResult(
        event_class=top_class,
        confidence=round(share * strength, 4),
        matched_rules=tuple(r.rule_id for r in matched[top_class]),
        runner_up=ranked[1][0] if len(ranked) > 1 else None,
        direction=event_direction(matched[top_class]),
    )
