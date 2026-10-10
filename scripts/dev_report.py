import argparse
import csv
from collections import Counter

from scripts.evaluate import CLASSES, SENTIMENTS, classification_report, per_class_scores
from src.riskengine.config import DATA_DIR
from src.riskengine.events import classify
from src.riskengine.normalize import clean_text
from src.riskengine.sentiment.vader import VaderSentiment

EVAL_DIR = DATA_DIR / "eval"


def read_sheet(name: str) -> list[dict]:
    with (EVAL_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["event_class"]]


def score_rows(rows: list[dict], sentiment_model) -> list[dict]:
    texts = [clean_text(row["text"]) for row in rows]
    sentiments = sentiment_model.score(texts)
    scored = []
    for row, text, sentiment in zip(rows, texts, sentiments):
        event = classify(text)
        scored.append({**row, "model_class": event.event_class, "model_sentiment": sentiment.label, "rules": ",".join(event.matched_rules)})
    return scored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", default="labels_w1_dev_sheet.csv")
    parser.add_argument("--errors", action="store_true")
    args = parser.parse_args()
    scored = score_rows(read_sheet(args.sheet), VaderSentiment())
    truth = [r["event_class"] for r in scored]
    predicted = [r["model_class"] for r in scored]
    print("event class", classification_report(truth, predicted, CLASSES))
    print("sentiment", classification_report([r["sentiment"] for r in scored], [r["model_sentiment"] for r in scored], SENTIMENTS))
    for label, scores in per_class_scores(truth, predicted, CLASSES).items():
        print(f"  {label:20s} p={scores['precision']:.2f} r={scores['recall']:.2f} f1={scores['f1']:.2f} n={scores['support']}")
    print("confusions", Counter((t, p) for t, p in zip(truth, predicted) if t != p).most_common(12))
    if args.errors:
        for row in scored:
            if row["event_class"] != row["model_class"]:
                print(f"{row['item_id']} truth={row['event_class']} model={row['model_class']} rules={row['rules']} | {row['text'][:110]}")


if __name__ == "__main__":
    main()
