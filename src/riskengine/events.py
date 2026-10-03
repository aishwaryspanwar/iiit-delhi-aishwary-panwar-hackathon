import re
from dataclasses import dataclass
from functools import lru_cache

from src.riskengine.config import load_yaml
from src.riskengine.models import EventResult


@dataclass(frozen=True)
class Rule:
    rule_id: str
    event_class: str
    weight: float
    patterns: tuple[re.Pattern[str], ...]


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    return load_yaml("taxonomy_rules.yaml")


@lru_cache(maxsize=1)
def compiled_rules() -> tuple[Rule, ...]:
    return tuple(
        Rule(
            rule_id=rule["id"],
            event_class=rule["class"],
            weight=float(rule["weight"]),
            patterns=tuple(re.compile(p, re.IGNORECASE) for p in rule["patterns"]),
        )
        for rule in taxonomy()["rules"]
    )


def class_display_name(event_class: str) -> str:
    return taxonomy()["classes"][event_class]


def classify(text: str) -> EventResult:
    settings = taxonomy()
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}
    for rule in compiled_rules():
        if any(p.search(text) for p in rule.patterns):
            scores[rule.event_class] = scores.get(rule.event_class, 0.0) + rule.weight
            matched.setdefault(rule.event_class, []).append(rule.rule_id)
    priority = {name: index for index, name in enumerate(settings["priority"])}
    ranked = sorted(scores.items(), key=lambda item: (-item[1], priority[item[0]]))
    if not ranked or ranked[0][1] < settings["min_score"]:
        all_rules = tuple(sorted(r for ids in matched.values() for r in ids))
        return EventResult(event_class="other", confidence=0.0, matched_rules=all_rules, runner_up=ranked[0][0] if ranked else None)
    top_class, top_score = ranked[0]
    share = top_score / sum(scores.values())
    strength = min(1.0, top_score / settings["confidence_saturation"])
    return EventResult(
        event_class=top_class,
        confidence=round(share * strength, 4),
        matched_rules=tuple(matched[top_class]),
        runner_up=ranked[1][0] if len(ranked) > 1 else None,
    )
