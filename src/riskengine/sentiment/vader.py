from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.riskengine.config import load_yaml
from src.riskengine.models import SentimentResult
from src.riskengine.sentiment.base import label_for


class VaderSentiment:
    def __init__(self) -> None:
        settings = load_yaml("normalization.yaml")
        self.analyzer = SentimentIntensityAnalyzer()
        self.analyzer.lexicon.update({k.lower(): float(v) for k, v in settings["sentiment_lexicon"].items()})
        self.name = f"vader@3.3.2+{settings['sentiment_lexicon_version']}"

    def score(self, texts: list[str]) -> list[SentimentResult]:
        results = []
        for text in texts:
            compound = round(float(self.analyzer.polarity_scores(text)["compound"]), 4)
            results.append(SentimentResult(score=compound, label=label_for(compound), model=self.name))
        return results
