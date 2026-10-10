from typing import Protocol

from src.riskengine.config import load_yaml
from src.riskengine.models import SentimentResult


def neutral_band(model: str) -> float:
    return float(load_yaml("normalization.yaml")["sentiment_neutral_band"][model])


def label_for(score: float, band: float) -> str:
    if score > band:
        return "pos"
    if score < -band:
        return "neg"
    return "neu"


class SentimentModel(Protocol):
    name: str

    def score(self, texts: list[str]) -> list[SentimentResult]: ...
