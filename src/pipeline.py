import argparse
from pathlib import Path

from src.riskengine.build import run_engine
from src.riskengine.config import PROCESSED_DIR
from src.riskengine.ingest.gdelt import gdelt_source_path, read_gdelt_documents
from src.riskengine.ingest.stub import read_stub_documents
from src.riskengine.ingest.tweets import read_tweet_documents, tweets_source_path
from src.riskengine.io import validate_records, write_json, write_jsonl
from src.riskengine.models import RawDoc
from src.stress.engine import run_all
from src.stress.portfolio_gen import PORTFOLIO_PATH, generate_portfolio, load_portfolio, write_portfolio


def read_window_documents(window: str) -> list[RawDoc]:
    docs = read_gdelt_documents(gdelt_source_path(window))
    tweets = tweets_source_path(window)
    return docs + read_tweet_documents(tweets) if tweets.exists() else docs


DATASETS = {
    "stub": read_stub_documents,
    "w1": lambda: read_window_documents("w1"),
    "w3": lambda: read_window_documents("w3"),
    "n1": lambda: read_window_documents("n1"),
}
DATASET_LABELS = {
    "w1": "W1 · Feb–Mar 2022 (GDELT + tweets)",
    "w3": "W3 · Sep 2022, Fed and gilt shock (GDELT + tweets)",
    "n1": "N1 · Aug–Sep 2026, calm market (GDELT news only)",
    "stub": "Stub sample (hand-written)",
}


def output_dir(dataset: str) -> Path:
    return PROCESSED_DIR / dataset


def available_datasets() -> list[str]:
    return [name for name in DATASET_LABELS if (PROCESSED_DIR / name / "signals_v1.jsonl.gz").exists()]


def load_sentiment_model(name: str):
    if name == "finbert":
        from src.riskengine.sentiment.finbert import FinbertSentiment

        return FinbertSentiment()
    from src.riskengine.sentiment.vader import VaderSentiment

    return VaderSentiment()


def run_pipeline(dataset: str, sentiment: str = "vader", out: Path | None = None) -> dict:
    target = out or output_dir(dataset)
    docs: list[RawDoc] = DATASETS[dataset]()
    signals, events = run_engine(docs, load_sentiment_model(sentiment))
    validate_records(signals, "signal_v1")
    validate_records(events, "event_v1")
    if not PORTFOLIO_PATH.exists():
        write_portfolio(generate_portfolio())
    results = run_all(load_portfolio(), events, signals)
    write_jsonl(target / "signals_v1.jsonl.gz", signals)
    write_jsonl(target / "events_v1.jsonl.gz", events)
    write_json(target / "stress_results_v1.json", results)
    return {"signals": len(signals), "events": len(events), "triggered": len(results["runs"]), "output": str(target)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="stub")
    parser.add_argument("--sentiment", choices=["vader", "finbert"], default="vader")
    args = parser.parse_args()
    print(run_pipeline(args.dataset, args.sentiment))


if __name__ == "__main__":
    main()
