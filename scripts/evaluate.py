import argparse
import csv
import hashlib
import json
import math
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from src.riskengine.config import DATA_DIR, ENGINE_VERSION, PROCESSED_DIR, config_hash
from src.riskengine.events import classify
from src.riskengine.io import read_json, read_jsonl
from src.riskengine.normalize import clean_text
from src.riskengine.sentiment.base import label_for, neutral_band
from src.riskengine.sentiment.vader import VaderSentiment

EVAL_DIR = DATA_DIR / "eval"
FINBERT_EVAL_SCORES = EVAL_DIR / "finbert_eval_scores.json"
CLASSES = ["geopolitical", "macroeconomic", "credit_event", "commodity_energy", "regulatory", "merger_acquisition", "earnings_corporate", "product_launch", "other"]
SENTIMENTS = ["neg", "neu", "pos"]
STRESS_CLASSES = {"geopolitical", "macroeconomic", "credit_event", "commodity_energy", "regulatory"}
MARKET_INDEX = "^GSPC"
VOLATILITY_INDEX = "^VIX"
RATE_CHANGE = "^TNX_change_bp"
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 20225
STRESS_DAY_ABS_RETURN = 0.015
STRESS_DAY_VIX_CHANGE = 0.10
US_CLOSE_UTC_HOUR = 21
REVIEWED_MARKS = {"y", "yes", "1", "x", "true"}
COMPARISON_WINDOWS = {
    "w1": {"returns": "returns_daily.csv", "start": "2022-02-10", "end": "2022-03-24", "role": "development and calibration"},
    "w3": {"returns": "returns_daily_w3.csv", "start": "2022-09-10", "end": "2022-09-30", "role": "untouched test, shock window"},
    "n1": {"returns": "returns_daily_n1.csv", "start": "2026-08-06", "end": "2026-09-04", "role": "untouched test, calm window"},
}
LABEL_SPLITS = {
    "w1_dev": {"sheet": "labels_w1_dev_sheet.csv", "key": "labels_w1_dev_key.csv", "window": "w1", "role": "development (LLM labels, used for tuning)"},
    "w1_test": {"sheet": "labels_sheet.csv", "key": "labels_key.csv", "window": "w1", "role": "test (human-verified)"},
    "w3_test": {"sheet": "labels_w3_test_sheet.csv", "key": "labels_w3_test_key.csv", "window": "w3", "role": "test (human-verified)"},
}
NAIVE_KEYWORDS = [
    ("credit_event", r"\b(default|downgrade|bankrupt)"),
    ("geopolitical", r"\b(war|invasion|invade|sanction|military|attack|troops)"),
    ("macroeconomic", r"\b(inflation|interest rate|fed\b|gdp|economy|recession)"),
    ("commodity_energy", r"\b(oil|gas|crude|wheat|commodit)"),
    ("regulatory", r"\b(regulator|fine[sd]?\b|lawsuit|probe|antitrust)"),
    ("merger_acquisition", r"\b(acquir|merger|takeover|buyout)"),
    ("earnings_corporate", r"\b(earnings|profit|revenue|ceo\b|shares)"),
    ("product_launch", r"\b(launch|unveil)"),
]


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


def bootstrap_interval(truth: list[str], predicted: list[str], metric, seed: int = BOOTSTRAP_SEED) -> list[float]:
    if not truth:
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(truth)
    values = []
    for _ in range(BOOTSTRAP_SAMPLES):
        picks = [rng.randrange(n) for _ in range(n)]
        values.append(metric([truth[i] for i in picks], [predicted[i] for i in picks]))
    values.sort()
    return [round(values[int(0.025 * BOOTSTRAP_SAMPLES)], 4), round(values[int(0.975 * BOOTSTRAP_SAMPLES) - 1], 4)]


def classification_report(truth: list[str], predicted: list[str], labels: list[str], intervals: bool = False) -> dict:
    majority = Counter(truth).most_common(1)[0][0]
    baseline = [majority] * len(truth)
    report = {
        "n": len(truth),
        "accuracy": round(accuracy(truth, predicted), 4),
        "macro_f1": round(macro_f1(truth, predicted, labels), 4),
        "majority_label": majority,
        "majority_accuracy": round(accuracy(truth, baseline), 4),
        "majority_macro_f1": round(macro_f1(truth, baseline, labels), 4),
    }
    if intervals:
        report["accuracy_ci95"] = bootstrap_interval(truth, predicted, accuracy)
        report["macro_f1_ci95"] = bootstrap_interval(truth, predicted, lambda t, p: macro_f1(t, p, labels))
    return report


def confusion(truth: list[str], predicted: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    return {t: {p: sum(a == t and b == p for a, b in zip(truth, predicted)) for p in labels} for t in labels}


def naive_keyword_class(text: str) -> str:
    lowered = text.lower()
    return next((label for label, pattern in NAIVE_KEYWORDS if re.search(pattern, lowered)), "other")


def text_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def finbert_scores(texts: list[str]) -> dict[str, float]:
    cached = json.loads(FINBERT_EVAL_SCORES.read_text(encoding="utf-8")) if FINBERT_EVAL_SCORES.exists() else {}
    missing = sorted({text_key(t): t for t in texts if text_key(t) not in cached}.items())
    if missing:
        from src.riskengine.sentiment.finbert import FinbertSentiment

        for (key, _), result in zip(missing, FinbertSentiment().score([t for _, t in missing])):
            cached[key] = result.score
        FINBERT_EVAL_SCORES.write_text(json.dumps(cached, indent=0, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return cached


def human_labels() -> tuple[dict[tuple[str, str], tuple[str, str]], list[dict]]:
    labels, blind = {}, []
    stage_a = EVAL_DIR / "human_verify_stage_a.csv"
    stage_b = EVAL_DIR / "human_verify_stage_b.csv"
    for path in (stage_a, stage_b):
        if not path.exists():
            continue
        for row in read_rows(path):
            reviewed = path == stage_a or row.get("reviewed", "").lower() in REVIEWED_MARKS
            if reviewed and row["event_class"] in CLASSES and row["sentiment"] in SENTIMENTS:
                labels[(row["window"], row["item_id"])] = (row["event_class"], row["sentiment"])
                if path == stage_a:
                    blind.append(row)
    return labels, blind


def labelled_items(split: str) -> list[dict]:
    spec = LABEL_SPLITS[split]
    keys = {row["item_id"]: row for row in read_rows(EVAL_DIR / spec["key"])}
    verified, _ = human_labels()
    items = []
    for row in read_rows(EVAL_DIR / spec["sheet"]):
        human = verified.get((spec["window"], row["item_id"])) if split != "w1_dev" else None
        event_class, sentiment = human if human else (row["event_class"], row["sentiment"])
        if event_class not in CLASSES or sentiment not in SENTIMENTS:
            raise ValueError(f"Invalid or missing label in {split} {row['item_id']}")
        items.append({
            "item_id": row["item_id"], "text": clean_text(row["text"]), "source": row["source_type"],
            "stratum": keys[row["item_id"]]["stratum"], "label_class": event_class, "label_sentiment": sentiment,
            "llm_class": row["event_class"], "llm_sentiment": row["sentiment"], "human_verified": human is not None,
        })
    return items


def score_items(items: list[dict]) -> list[dict]:
    texts = [item["text"] for item in items]
    vader = VaderSentiment().score(texts)
    finbert = finbert_scores(texts)
    band = neutral_band("finbert")
    for item, vader_result in zip(items, vader):
        event = classify(item["text"])
        item["model_class"] = event.event_class
        item["naive_class"] = naive_keyword_class(item["text"])
        item["vader_sentiment"] = vader_result.label
        item["finbert_sentiment"] = label_for(finbert[text_key(item["text"])], band)
    return items


def split_report(items: list[dict]) -> dict:
    truth_class = [i["label_class"] for i in items]
    truth_sentiment = [i["label_sentiment"] for i in items]
    return {
        "n": len(items),
        "human_verified": sum(i["human_verified"] for i in items),
        "label_counts": {"event_class": dict(sorted(Counter(truth_class).items())), "sentiment": dict(sorted(Counter(truth_sentiment).items()))},
        "event_class": classification_report(truth_class, [i["model_class"] for i in items], CLASSES, intervals=True),
        "event_class_naive_keywords": classification_report(truth_class, [i["naive_class"] for i in items], CLASSES, intervals=True),
        "sentiment_finbert": classification_report(truth_sentiment, [i["finbert_sentiment"] for i in items], SENTIMENTS, intervals=True),
        "sentiment_vader": classification_report(truth_sentiment, [i["vader_sentiment"] for i in items], SENTIMENTS, intervals=True),
        "per_class": per_class_scores(truth_class, [i["model_class"] for i in items], CLASSES),
        "confusion": confusion(truth_class, [i["model_class"] for i in items], CLASSES),
    }


def annotator_agreement(items_by_split: dict[str, list[dict]]) -> dict:
    _, blind = human_labels()
    lookup = {(LABEL_SPLITS[s]["window"], i["item_id"]): i for s, items in items_by_split.items() if s != "w1_dev" for i in items}
    pairs = [(lookup[(row["window"], row["item_id"])], row) for row in blind if (row["window"], row["item_id"]) in lookup]
    if not pairs:
        return {"n": 0}
    llm_class, human_class = [p[0]["llm_class"] for p in pairs], [p[1]["event_class"] for p in pairs]
    llm_sentiment, human_sentiment = [p[0]["llm_sentiment"] for p in pairs], [p[1]["sentiment"] for p in pairs]
    return {
        "n": len(pairs),
        "event_class_agreement": round(accuracy(llm_class, human_class), 4),
        "event_class_kappa": round(cohen_kappa(llm_class, human_class), 4),
        "sentiment_agreement": round(accuracy(llm_sentiment, human_sentiment), 4),
        "sentiment_kappa": round(cohen_kappa(llm_sentiment, human_sentiment), 4),
    }


def relabel_agreement() -> dict:
    first = {row["item_id"]: row for row in read_rows(EVAL_DIR / "labels_sheet.csv")}
    key = {row["relabel_id"]: row["item_id"] for row in read_rows(EVAL_DIR / "relabel_key.csv")}
    pairs = [(first[key[row["item_id"]]], row) for row in read_rows(EVAL_DIR / "relabel_sheet.csv")]
    return {
        "n": len(pairs),
        "event_class_agreement": round(accuracy([a["event_class"] for a, _ in pairs], [b["event_class"] for _, b in pairs]), 4),
        "event_class_kappa": round(cohen_kappa([a["event_class"] for a, _ in pairs], [b["event_class"] for _, b in pairs]), 4),
        "sentiment_agreement": round(accuracy([a["sentiment"] for a, _ in pairs], [b["sentiment"] for _, b in pairs]), 4),
        "sentiment_kappa": round(cohen_kappa([a["sentiment"] for a, _ in pairs], [b["sentiment"] for _, b in pairs]), 4),
    }


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        for index in order[position:end + 1]:
            result[index] = (position + end) / 2.0 + 1.0
        position = end + 1
    return result


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(ranks(x), ranks(y))


def spearman_with_interval(x: list[float], y: list[float]) -> dict:
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(x)
    values = []
    for _ in range(BOOTSTRAP_SAMPLES):
        picks = [rng.randrange(n) for _ in range(n)]
        values.append(spearman([x[i] for i in picks], [y[i] for i in picks]))
    values.sort()
    return {"n": n, "rho": round(spearman(x, y), 4), "ci95": [round(values[int(0.025 * BOOTSTRAP_SAMPLES)], 4), round(values[int(0.975 * BOOTSTRAP_SAMPLES) - 1], 4)]}


def market_rows(window: str) -> list[dict]:
    spec = COMPARISON_WINDOWS[window]
    rows = read_rows(DATA_DIR / "market" / spec["returns"])
    return [row for row in rows if row[MARKET_INDEX]]


def window_days(window: str) -> list[dict]:
    spec = COMPARISON_WINDOWS[window]
    return [row for row in market_rows(window) if spec["start"] <= row["date"] <= spec["end"]]


def stress_day(row: dict) -> bool:
    return abs(float(row[MARKET_INDEX])) > STRESS_DAY_ABS_RETURN or float(row[VOLATILITY_INDEX]) > STRESS_DAY_VIX_CHANGE


def trading_day_for(timestamp: str, days: list[str]) -> str | None:
    moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    day = moment.strftime("%Y-%m-%d")
    if moment.hour >= US_CLOSE_UTC_HOUR:
        day = (moment + timedelta(days=1)).strftime("%Y-%m-%d")
    return next((d for d in days if d >= day), None)


def daily_max_impact(events: list[dict]) -> dict[str, float]:
    by_day: dict[str, float] = {}
    for event in events:
        if event["class"] in STRESS_CLASSES and not event["warmup"]:
            day = event["cluster_id"][:10]
            by_day[day] = max(by_day.get(day, 1.0), event["impact"])
    return by_day


def impact_market_link(windows: list[str]) -> dict:
    result, pooled = {}, {"impact": [], "abs_sp500": [], "vix_change": [], "abs_rate_change": []}
    for window in windows:
        events = read_jsonl(PROCESSED_DIR / window / "events_v1.jsonl.gz")
        impacts = daily_max_impact(events)
        warmup_end = (datetime.fromisoformat(COMPARISON_WINDOWS[window]["start"]) + timedelta(days=3)).strftime("%Y-%m-%d")
        rows = [row for row in window_days(window) if row["date"] >= warmup_end]
        series = {
            "impact": [impacts.get(row["date"], 1.0) for row in rows],
            "abs_sp500": [abs(float(row[MARKET_INDEX])) for row in rows],
            "vix_change": [float(row[VOLATILITY_INDEX]) for row in rows],
            "abs_rate_change": [abs(float(row[RATE_CHANGE])) for row in rows],
        }
        for name, values in series.items():
            pooled[name] += values
        result[window] = {target: spearman_with_interval(series["impact"], series[target]) for target in ("abs_sp500", "vix_change", "abs_rate_change")}
    result["pooled"] = {target: spearman_with_interval(pooled["impact"], pooled[target]) for target in ("abs_sp500", "vix_change", "abs_rate_change")}
    return result


def detection_quality(flag_days: set[str], days: list[str], stress: set[str]) -> dict:
    index = {d: i for i, d in enumerate(days)}
    hits = sum(1 for d in flag_days if d in stress or (index[d] + 1 < len(days) and days[index[d] + 1] in stress))
    covered = sum(1 for d in stress if d in flag_days or (index[d] > 0 and days[index[d] - 1] in flag_days))
    return {
        "flags": len(flag_days),
        "precision": round(hits / len(flag_days), 4) if flag_days else None,
        "recall": round(covered / len(stress), 4) if stress else None,
    }


def naive_volume_flags(signals: list[dict], days: list[str]) -> set[str]:
    counts = Counter(s["published_at"][:10] for s in signals if s["event"]["class"] in STRESS_CLASSES)
    calendar = sorted(counts)
    flagged = set()
    for position, day in enumerate(calendar):
        history = [counts[d] for d in calendar[max(0, position - 7):position]]
        if len(history) >= 3 and counts[day] > 2.0 * sorted(history)[len(history) // 2]:
            stamp = trading_day_for(f"{day}T00:00:00Z", days)
            if stamp:
                flagged.add(stamp)
    return flagged


def trigger_quality(windows: list[str]) -> dict:
    result = {}
    for window in windows:
        rows = window_days(window)
        days = [row["date"] for row in rows]
        stress = {row["date"] for row in rows if stress_day(row)}
        alerts = read_jsonl(PROCESSED_DIR / window / "alerts_v1.jsonl.gz")
        signals = read_jsonl(PROCESSED_DIR / window / "signals_v1.jsonl.gz")
        events = read_jsonl(PROCESSED_DIR / window / "events_v1.jsonl.gz")
        engine_flags = {d for d in (trading_day_for(a["detected_at"], days) for a in alerts) if d}
        threshold_flags = {d for d in (trading_day_for(e["peak_at"], days) for e in events if e["class"] in STRESS_CLASSES and e["impact"] > 7.0) if d}
        every_day = set(days)
        result[window] = {
            "trading_days": len(days),
            "stress_days": len(stress),
            "base_rate": round(len(stress) / len(days), 4) if days else None,
            "engine_alerts": detection_quality(engine_flags, days, stress),
            "impact_above_7_without_gates": detection_quality(threshold_flags, days, stress),
            "naive_headline_volume_spike": detection_quality(naive_volume_flags(signals, days), days, stress),
            "naive_fire_every_day": detection_quality(every_day, days, stress),
        }
    return result


def lead_times(windows: list[str]) -> dict:
    result = {}
    for window in windows:
        alerts = read_jsonl(PROCESSED_DIR / window / "alerts_v1.jsonl.gz")
        rows = []
        for alert in alerts:
            detected = datetime.fromisoformat(alert["detected_at"].replace("Z", "+00:00"))
            day_end = datetime.fromisoformat(alert["day_end_at"].replace("Z", "+00:00")) + timedelta(seconds=1)
            first = datetime.fromisoformat(alert["first_headline_at"].replace("Z", "+00:00"))
            close = detected.replace(hour=US_CLOSE_UTC_HOUR, minute=0, second=0)
            rows.append({
                "alert_id": alert["alert_id"],
                "hours_before_end_of_day_batch": round((day_end - detected).total_seconds() / 3600, 1),
                "hours_after_first_headline": round((detected - first).total_seconds() / 3600, 1),
                "before_us_close": detected <= close,
            })
        result[window] = {
            "alerts": len(rows),
            "median_hours_before_end_of_day_batch": percentile([r["hours_before_end_of_day_batch"] for r in rows], 0.5) if rows else None,
            "median_hours_after_first_headline": percentile([r["hours_after_first_headline"] for r in rows], 0.5) if rows else None,
            "share_before_us_close": round(sum(r["before_us_close"] for r in rows) / len(rows), 4) if rows else None,
            "alerts_detail": rows,
        }
    return result


def available_windows() -> list[str]:
    return [w for w in COMPARISON_WINDOWS if (PROCESSED_DIR / w / "alerts_v1.jsonl.gz").exists()]


def evaluate() -> dict:
    items_by_split = {split: score_items(labelled_items(split)) for split in LABEL_SPLITS}
    windows = available_windows()
    report = {
        "engine_version": ENGINE_VERSION,
        "config_hash": config_hash(),
        "splits": {},
        "llm_vs_human_blind": annotator_agreement(items_by_split),
        "llm_repeat_labelling": relabel_agreement(),
        "impact_vs_market": impact_market_link(windows),
        "trigger_quality": trigger_quality(windows),
        "alert_lead_times": lead_times(windows),
        "definitions": {
            "stress_day": f"|S&P 500 return| > {STRESS_DAY_ABS_RETURN:.1%} or VIX change > {STRESS_DAY_VIX_CHANGE:.0%} on the day",
            "hit": "a flag counts as a hit if its trading day or the next one is a stress day; a stress day counts as covered if it or the previous trading day is flagged",
            "trading_day": f"alerts after {US_CLOSE_UTC_HOUR}:00 UTC map to the next trading day",
        },
    }
    for split, items in items_by_split.items():
        representative = [i for i in items if not i["stratum"].startswith("oversample")]
        report["splits"][split] = {"role": LABEL_SPLITS[split]["role"], "representative": split_report(representative)}
        if len(representative) != len(items):
            report["splits"][split]["all_items_including_oversample"] = split_report(items)
    return report


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = share * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def market_summary(window: str) -> dict:
    returns = [float(row[MARKET_INDEX]) for row in window_days(window)]
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
        "role": window["role"],
        "window": {"start": window["start"], "end": window["end"]},
        "signals": len(signals),
        "sources": dict(sorted(Counter(s["source"] for s in signals).items())),
        "signal_class_share": {k: round(v / len(signals), 4) for k, v in sorted(classes.items())},
        "entity_coverage": round(sum(1 for s in signals if s["entities"]) / len(signals), 4),
        "clusters": len(events),
        "cluster_impact_p50": round(percentile(impacts, 0.5), 2),
        "cluster_impact_p90": round(percentile(impacts, 0.9), 2),
        "cluster_impact_p99": round(percentile(impacts, 0.99), 2),
        "cluster_impact_max": round(max(impacts), 2) if impacts else 0.0,
        "clusters_above_threshold": sum(1 for i in impacts if i > threshold),
        "stress_tests_triggered": len(stress["runs"]),
        "runs": [
            {"date": r["t_start"][:10], "detected_at": r.get("detected_at"), "class": r["class"], "scope_targets": r["scope_targets"], "impact": r["impact"], "pnl": r["totals"]["pnl"], "pnl_pct": r["totals"]["pnl_pct"]}
            for r in stress["runs"]
        ],
        "failed_checks": dict(sorted(Counter(c for d in stress["decisions"] if not d["triggered"] for c in d["failed"]).items())),
        "market": market_summary(dataset),
    }


def compare_windows() -> dict:
    return {name: window_summary(name) for name in available_windows()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(EVAL_DIR / "metrics.json"))
    args = parser.parse_args()
    metrics = evaluate()
    Path(args.out).write_text(json.dumps(metrics, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    comparison = compare_windows()
    (EVAL_DIR / "window_comparison.json").write_text(json.dumps(comparison, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({s: {k: v["representative"][k] for k in ("n", "human_verified", "event_class", "sentiment_finbert")} for s, v in metrics["splits"].items()}, indent=1))


if __name__ == "__main__":
    main()
