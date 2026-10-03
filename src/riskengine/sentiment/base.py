from typing import Protocol

from src.riskengine.models import SentimentResult

NEUTRAL_BAND = 0.05


def label_for(score: float) -> str:
    if score > NEUTRAL_BAND:
        return "pos"
    if score < -NEUTRAL_BAND:
        return "neg"
    return "neu"


class SentimentModel(Protocol):
    name: str

    def score(self, texts: list[str]) -> list[SentimentResult]: ...
