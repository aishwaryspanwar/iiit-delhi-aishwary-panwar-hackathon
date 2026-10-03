import math
import re
from functools import lru_cache

from src.riskengine.config import load_yaml
from src.riskengine.models import Entity


@lru_cache(maxsize=1)
def rubric() -> dict:
    return load_yaml("impact.yaml")


@lru_cache(maxsize=1)
def cue_patterns() -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in rubric()["cue_patterns"])


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def cue_component(text: str) -> float:
    hits = sum(len(p.findall(text)) for p in cue_patterns())
    return round(min(1.0, hits / rubric()["cue_full_at"]), 4)


def impact_components(event_class: str, sentiment_score: float, entities: list[Entity], text: str) -> dict[str, float]:
    settings = rubric()
    importance = max((e.importance for e in entities), default=settings["default_entity_importance"])
    return {
        "class_prior": float(settings["class_prior"][event_class]),
        "sentiment_mag": round(abs(sentiment_score), 4),
        "entity_importance": float(importance),
        "cue_bonus": cue_component(text),
    }


def item_impact(components: dict[str, float]) -> float:
    weights = rubric()["weights"]
    weighted = sum(weights[name] * value for name, value in components.items())
    return round(clip(1.0 + 9.0 * weighted, 1.0, 10.0), 1)


def breadth_term(n_outlets: int) -> float:
    return round(rubric()["breadth_coefficient"] * math.log(max(1, n_outlets)), 4)


def cluster_impact(item_impacts: list[float], n_outlets: int) -> tuple[float, float, float]:
    top = sorted(item_impacts, reverse=True)[: rubric()["cluster_top_k"]]
    aggregate = round(sum(top) / len(top), 4)
    breadth = breadth_term(n_outlets)
    return aggregate, breadth, round(clip(aggregate + breadth, 1.0, 10.0), 1)
