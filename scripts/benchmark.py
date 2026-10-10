import argparse
import json
import platform
import time
from pathlib import Path

from src.pipeline import DATASETS
from src.riskengine.build import to_signal
from src.riskengine.config import DATA_DIR, ENGINE_VERSION, config_hash
from src.riskengine.dedup import clean_and_dedup
from src.riskengine.sentiment.loader import finbert_available, load_sentiment_model
from src.stream.engine import run_stream

BENCHMARK_PATH = DATA_DIR / "eval" / "benchmark.json"
FINBERT_SAMPLE = 512


def timed(function, *args):
    started = time.perf_counter()
    result = function(*args)
    return result, time.perf_counter() - started


def benchmark(dataset: str) -> dict:
    raw, load_seconds = timed(DATASETS[dataset])
    docs, clean_seconds = timed(clean_and_dedup, raw)
    vader = load_sentiment_model("vader")
    sentiments, vader_seconds = timed(vader.score, [d.text for d in docs])
    build = {"build_id": "benchmark", "engine_version": ENGINE_VERSION, "config_hash": config_hash()}
    signals, signal_seconds = timed(lambda: [to_signal(d, s, build) for d, s in zip(docs, sentiments)])
    _, stream_seconds = timed(run_stream, signals)
    result = {
        "dataset": dataset,
        "machine": {"python": platform.python_version(), "processor": platform.processor(), "system": platform.system()},
        "raw_items": len(raw),
        "deduplicated_items": len(docs),
        "seconds": {
            "load": round(load_seconds, 2), "clean_and_dedup": round(clean_seconds, 2), "sentiment_vader": round(vader_seconds, 2),
            "rules_entities_impact": round(signal_seconds, 2), "stream_clusters_alerts": round(stream_seconds, 2),
        },
        "items_per_second_vader_pipeline": round(len(docs) / (clean_seconds + vader_seconds + signal_seconds + stream_seconds), 1),
    }
    if finbert_available():
        model = load_sentiment_model("finbert")
        sample = [d.text for d in docs[:FINBERT_SAMPLE]]
        _, finbert_seconds = timed(model.raw_scores, sample)
        result["finbert_items_per_second_cpu"] = round(len(sample) / finbert_seconds, 1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="w1")
    parser.add_argument("--out", type=Path, default=BENCHMARK_PATH)
    args = parser.parse_args()
    result = benchmark(args.dataset)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
