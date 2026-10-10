from importlib.util import find_spec

BUILD_DEFAULT = "finbert"


def finbert_available() -> bool:
    return find_spec("torch") is not None and find_spec("transformers") is not None


def load_sentiment_model(name: str):
    if name == "finbert":
        from src.riskengine.sentiment.finbert import FinbertSentiment

        return FinbertSentiment()
    from src.riskengine.sentiment.vader import VaderSentiment

    return VaderSentiment()


def load_live_model():
    if finbert_available():
        try:
            return load_sentiment_model("finbert")
        except (OSError, RuntimeError, ValueError):
            pass
    return load_sentiment_model("vader")
