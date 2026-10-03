import argparse
import csv
from pathlib import Path

from src.riskengine.config import DATA_DIR, PROCESSED_DIR
from src.riskengine.io import read_jsonl
from src.riskengine.sentiment.finbert import FinbertSentiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="w1")
    args = parser.parse_args()
    signals = read_jsonl(PROCESSED_DIR / args.dataset / "signals_v1.jsonl.gz")
    model = FinbertSentiment()
    scores = model.score([s["text"] or "" for s in signals])
    output = DATA_DIR / "eval" / f"sentiment_finbert_{args.dataset}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["signal_id", "finbert_score", "finbert_label", "model"])
        for signal, result in sorted(zip(signals, scores), key=lambda pair: pair[0]["signal_id"]):
            writer.writerow([signal["signal_id"], f"{result.score:.4f}", result.label, result.model])
    print(f"scored {len(scores)} -> {output}")


if __name__ == "__main__":
    main()
