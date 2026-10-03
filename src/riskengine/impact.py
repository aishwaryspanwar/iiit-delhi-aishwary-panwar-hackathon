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


def baseline_mentions(history: list[int]) -> float:
    default = float(rubric()["cluster"]["default_baseline_mentions"])
    if not history:
        return default
    ordered = sorted(history)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return max(default, float(median))


def cluster_components(item_impacts: list[float], n_outlets: int, n_mentions: int, baseline: float) -> dict[str, float]:
    settings = rubric()["cluster"]
    top = sorted(item_impacts, reverse=True)[: settings["top_k"]]
    severity = (sum(top) / len(top) - 1.0) / 9.0
    breadth = math.log(max(1, n_outlets)) / math.log(settings["breadth_full_at_outlets"])
    volume = math.log2(max(n_mentions, 1) / baseline) / settings["volume_full_at_log2_ratio"]
    return {
        "severity": round(clip(severity, 0.0, 1.0), 4),
        "breadth": round(clip(breadth, 0.0, 1.0), 4),
        "abnormal_volume": round(clip(volume, 0.0, 1.0), 4),
    }


def cluster_impact(components: dict[str, float]) -> float:
    weights = rubric()["cluster"]["weights"]
    weighted = sum(weights[name] * value for name, value in components.items())
    return round(clip(1.0 + 9.0 * weighted, 1.0, 10.0), 1)
