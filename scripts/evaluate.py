import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from src.riskengine.config import DATA_DIR, PROCESSED_DIR
from src.riskengine.io import read_json, read_jsonl

EVAL_DIR = DATA_DIR / "eval"
CLASSES = ["geopolitical", "macroeconomic", "credit_event", "commodity_energy", "regulatory", "merger_acquisition", "earnings_corporate", "product_launch", "other"]
SENTIMENTS = ["neg", "neu", "pos"]
MARKET_INDEX = "^GSPC"
COMPARISON_WINDOWS = {
    "w1": {"returns": "returns_daily.csv", "start": "2022-02-10", "end": "2022-03-24"},
    "n1": {"returns": "returns_daily_n1.csv", "start": "2026-08-06", "end": "2026-09-04"},
}
VOLATILITY_INDEX = "^VIX"


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def accuracy(truth: list[str], predicted: list[str]) -> float:
    return sum(t == p for t, p in zip(truth, predicted)) / len(truth) if truth else 0.0


def per_class_scores(truth: list[str], predicted: list[str], labels: list[str]) -> dict[str, dict[str, float]]:
    scores = {}
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(truth, predicted))
        fp = sum(t != label and p == label for t, p in zip(truth, predicted))
        fn = sum(t == label and p != label for t, p in zip(truth, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "support": tp + fn}
    return scores


def macro_f1(truth: list[str], predicted: list[str], labels: list[str]) -> float:
    present = [label for label in labels if label in truth]
    if not present:
        return 0.0
    scores = per_class_scores(truth, predicted, present)
    return sum(scores[label]["f1"] for label in present) / len(present)


def cohen_kappa(first: list[str], second: list[str]) -> float:
    n = len(first)
    if n == 0:
        return 0.0
    observed = accuracy(first, second)
    left, right = Counter(first), Counter(second)
    expected = sum(left[label] * right[label] for label in set(first) | set(second)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def confusion(truth: list[str], predicted: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    return {t: {p: sum(a == t and b == p for a, b in zip(truth, predicted)) for p in labels} for t in labels}


def classification_report(truth: list[str], predicted: list[str], labels: list[str]) -> dict:
    majority = Counter(truth).most_common(1)[0][0]
    baseline = [majority] * len(truth)
    return {
        "n": len(truth),
        "accuracy": round(accuracy(truth, predicted), 4),
        "macro_f1": round(macro_f1(truth, predicted, labels), 4),
        "majority_label": majority,
        "majority_accuracy": round(accuracy(truth, baseline), 4),
        "majority_macro_f1": round(macro_f1(truth, baseline, labels), 4),
    }


def impact_market_check(dataset: str) -> dict:
    stress = read_json(PROCESSED_DIR / dataset / "stress_results_v1.json")
    with (DATA_DIR / "market" / "returns_daily.csv").open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row[MARKET_INDEX]]
    window = [row for row in rows if "2022-02-10" <= row["date"] <= "2022-03-24"]
    days = [row["date"] for row in window]
    by_day = {row["date"]: row for row in window}
    triggers = []
    for run in stress["runs"]:
        day = run["t_start"][:10]
        trading = next((d for d in days if d >= day), None)
        if trading is None:
            continue
        triggers.append({
            "event_date": day,
            "trading_date": trading,
            "class": run["class"],
            "impact": run["impact"],
            "sp500_return": round(float(by_day[trading][MARKET_INDEX]), 5),
            "vix_change": round(float(by_day[trading][VOLATILITY_INDEX]), 5),
        })
    trigger_days = {t["trading_date"] for t in triggers}
    abs_all = [abs(float(by_day[d][MARKET_INDEX])) for d in days]
    abs_trigger = [abs(float(by_day[d][MARKET_INDEX])) for d in trigger_days]
    return {
        "window_trading_days": len(days),
        "trigger_trading_days": len(trigger_days),
        "mean_abs_sp500_return_all_days": round(sum(abs_all) / len(abs_all), 5),
        "mean_abs_sp500_return_trigger_days": round(sum(abs_trigger) / len(abs_trigger), 5) if abs_trigger else None,
        "triggers": triggers,
    }


def evaluate(dataset: str = "w1") -> dict:
    labels = read_rows(EVAL_DIR / "labels_sheet.csv")
    key = {row["item_id"]: row for row in read_rows(EVAL_DIR / "labels_key.csv")}
    relabels = read_rows(EVAL_DIR / "relabel_sheet.csv")
    relabel_key = {row["relabel_id"]: row["item_id"] for row in read_rows(EVAL_DIR / "relabel_key.csv")}
    signals = {s["signal_id"]: s for s in read_jsonl(PROCESSED_DIR / dataset / "signals_v1.jsonl.gz")}
    finbert = {row["signal_id"]: row["finbert_label"] for row in read_rows(EVAL_DIR / "sentiment_finbert_w1.csv")}

    items = []
    for row in labels:
        if row["event_class"] not in CLASSES or row["sentiment"] not in SENTIMENTS:
            raise ValueError(f"Invalid or missing label in {row['item_id']}")
        signal = signals[key[row["item_id"]]["signal_id"]]
        items.append({
            "item_id": row["item_id"],
            "stratum": key[row["item_id"]]["stratum"],
            "source": "news" if signal["source"] == "gdelt_gkg" else "tweet",
            "human_class": row["event_class"],
            "human_sentiment": row["sentiment"],
            "model_class": signal["event"]["class"],
            "vader_sentiment": signal["sentiment"]["label"],
            "finbert_sentiment": finbert[signal["signal_id"]],
        })

    def subset(name: str, rows: list[dict]) -> dict:
        human_class = [r["human_class"] for r in rows]
        human_sentiment = [r["human_sentiment"] for r in rows]
        return {
            "name": name,
            "event_class": classification_report(human_class, [r["model_class"] for r in rows], CLASSES),
            "sentiment_vader": classification_report(human_sentiment, [r["vader_sentiment"] for r in rows], SENTIMENTS),
            "sentiment_finbert": classification_report(human_sentiment, [r["finbert_sentiment"] for r in rows], SENTIMENTS),
        }

    representative = [r for r in items if r["stratum"].startswith("stratified")]
    first_pass = {r["item_id"]: r for r in items}
    pairs = [(first_pass[relabel_key[row["item_id"]]], row) for row in relabels]
    return {
        "dataset": dataset,
        "label_counts": {
            "event_class": dict(sorted(Counter(r["human_class"] for r in items).items())),
            "sentiment": dict(sorted(Counter(r["human_sentiment"] for r in items).items())),
        },
        "representative": subset("stratified sample (representative)", representative),
        "representative_news": subset("stratified sample, news only", [r for r in representative if r["source"] == "news"]),
        "representative_tweets": subset("stratified sample, tweets only", [r for r in representative if r["source"] == "tweet"]),
        "all_items": subset("all 150 items (includes model-class oversample)", items),
        "per_class_all_items": per_class_scores([r["human_class"] for r in items], [r["model_class"] for r in items], CLASSES),
        "confusion_all_items": confusion([r["human_class"] for r in items], [r["model_class"] for r in items], CLASSES),
        "relabel_agreement": {
            "n": len(pairs),
            "event_class_agreement": round(accuracy([a["human_class"] for a, _ in pairs], [b["event_class"] for _, b in pairs]), 4),
            "event_class_kappa": round(cohen_kappa([a["human_class"] for a, _ in pairs], [b["event_class"] for _, b in pairs]), 4),
            "sentiment_agreement": round(accuracy([a["human_sentiment"] for a, _ in pairs], [b["sentiment"] for _, b in pairs]), 4),
            "sentiment_kappa": round(cohen_kappa([a["human_sentiment"] for a, _ in pairs], [b["sentiment"] for _, b in pairs]), 4),
        },
        "impact_market_check": impact_market_check(dataset),
    }


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = share * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def market_summary(returns_file: str, start: str, end: str) -> dict:
    with (DATA_DIR / "market" / returns_file).open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if start <= row["date"] <= end and row[MARKET_INDEX]]
    returns = [float(row[MARKET_INDEX]) for row in rows]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return {
        "trading_days": len(returns),
        "sp500_annualised_volatility": round(math.sqrt(variance) * math.sqrt(252), 4),
        "sp500_mean_abs_daily_return": round(sum(abs(r) for r in returns) / len(returns), 5),
        "sp500_worst_day": round(min(returns), 5),
        "sp500_window_return": round(math.prod(1 + r for r in returns) - 1, 5),
    }


def window_summary(dataset: str) -> dict:
    window = COMPARISON_WINDOWS[dataset]
    folder = PROCESSED_DIR / dataset
    signals = read_jsonl(folder / "signals_v1.jsonl.gz")
    events = read_jsonl(folder / "events_v1.jsonl.gz")
    stress = read_json(folder / "stress_results_v1.json")
    threshold = stress["trigger_settings"]["impact_threshold"]
    impacts = [e["impact"] for e in events]
    classes = Counter(s["event"]["class"] for s in signals)
    return {
        "dataset": dataset,
        "window": {"start": window["start"], "end": window["end"]},
        "signals": len(signals),
        "sources": dict(sorted(Counter(s["source"] for s in signals).items())),
        "signal_class_share": {k: round(v / len(signals), 4) for k, v in sorted(classes.items())},
        "clusters": len(events),
        "cluster_impact_p50": round(percentile(impacts, 0.5), 2),
        "cluster_impact_p90": round(percentile(impacts, 0.9), 2),
        "cluster_impact_p99": round(percentile(impacts, 0.99), 2),
        "cluster_impact_max": round(max(impacts), 2) if impacts else 0.0,
        "clusters_above_threshold": sum(1 for i in impacts if i > threshold),
        "stress_tests_triggered": len(stress["runs"]),
        "runs": [
            {"date": r["t_start"][:10], "class": r["class"], "impact": r["impact"], "pnl": r["totals"]["pnl"], "pnl_pct": r["totals"]["pnl_pct"]}
            for r in stress["runs"]
        ],
        "failed_checks": dict(sorted(Counter(c for d in stress["decisions"] if not d["triggered"] for c in d["failed"]).items())),
        "market": market_summary(window["returns"], window["start"], window["end"]),
    }


def compare_windows() -> dict:
    return {name: window_summary(name) for name in COMPARISON_WINDOWS if (PROCESSED_DIR / name / "events_v1.jsonl.gz").exists()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="w1")
    parser.add_argument("--out", default=str(EVAL_DIR / "metrics.json"))
    args = parser.parse_args()
    metrics = evaluate(args.dataset)
    Path(args.out).write_text(json.dumps(metrics, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    comparison = compare_windows()
    (EVAL_DIR / "window_comparison.json").write_text(json.dumps(comparison, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: metrics[k] for k in ("representative", "relabel_agreement")}, indent=1))


if __name__ == "__main__":
    main()
