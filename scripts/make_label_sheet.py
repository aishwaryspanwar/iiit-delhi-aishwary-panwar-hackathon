import argparse
import csv
import random
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.riskengine.build import signal_id_for
from src.riskengine.config import DATA_DIR, PROCESSED_DIR
from src.riskengine.dedup import clean_and_dedup
from src.riskengine.io import read_jsonl

EVAL_DIR = DATA_DIR / "eval"
SEED = 20221
STRATIFIED_TOTAL = 100
NEWS_SHARE = 0.7
OVERSAMPLE_PER_CLASS = {"credit_event": 9, "regulatory": 8, "merger_acquisition": 8, "product_launch": 8, "macroeconomic": 9, "commodity_energy": 8}
SHEET_FIELDS = ["item_id", "date", "source_type", "text", "event_class", "sentiment", "notes"]
RELABEL_SIZE = 30


def iso_week(published_at: str) -> int:
    return date.fromisoformat(published_at[:10]).isocalendar()[1]


def source_type(signal: dict) -> str:
    return "news" if signal["source"] == "gdelt_gkg" else "tweet"


def stratified_sample(signals: list[dict], rng: random.Random, size: int = STRATIFIED_TOTAL) -> list[tuple[dict, str]]:
    strata: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for signal in signals:
        strata[(source_type(signal), iso_week(signal["published_at"]))].append(signal)
    picked = []
    kinds = {k[0] for k in strata}
    shares = (("news", NEWS_SHARE), ("tweet", 1 - NEWS_SHARE)) if kinds == {"news", "tweet"} else ((next(iter(kinds)), 1.0),)
    for kind, share in shares:
        keys = sorted(k for k in strata if k[0] == kind)
        quota = round(size * share)
        total = sum(len(strata[k]) for k in keys)
        allocations = {k: max(1, round(quota * len(strata[k]) / total)) for k in keys}
        while sum(allocations.values()) > quota:
            largest = max(allocations, key=lambda k: (allocations[k], k))
            allocations[largest] -= 1
        while sum(allocations.values()) < quota:
            largest = max(keys, key=lambda k: (len(strata[k]) - allocations[k], k))
            allocations[largest] += 1
        for key in keys:
            members = sorted(strata[key], key=lambda s: s["signal_id"])
            picked += [(s, f"stratified:{key[0]}:week{key[1]}") for s in rng.sample(members, allocations[key])]
    return picked


def oversample(signals: list[dict], exclude: set[str], rng: random.Random) -> list[tuple[dict, str]]:
    picked = []
    for event_class, count in sorted(OVERSAMPLE_PER_CLASS.items()):
        pool = sorted((s for s in signals if s["event"]["class"] == event_class and s["signal_id"] not in exclude), key=lambda s: s["signal_id"])
        picked += [(s, f"oversample:{event_class}") for s in rng.sample(pool, min(count, len(pool)))]
    return picked


def write_rows(path, fields, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_existing_keys(paths: list[Path]) -> set[str]:
    excluded = set()
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            excluded |= {row["signal_id"] for row in csv.DictReader(handle)}
    return excluded


def blind_documents(window: str) -> list[dict]:
    from src.pipeline import read_window_documents

    return [
        {"signal_id": signal_id_for(doc.source, doc.source_id), "source": doc.source, "published_at": doc.published_at.strftime("%Y-%m-%dT%H:%M:%SZ"), "text": doc.text}
        for doc in clean_and_dedup(read_window_documents(window))
    ]


def split_sheet(window: str, split: str, size: int, seed: int, prefix: str, exclude: set[str]) -> None:
    rng = random.Random(seed)
    pool = blind_documents(window) if split == "test" else read_jsonl(PROCESSED_DIR / window / "signals_v1.jsonl.gz")
    signals = [s for s in pool if s["text"] and s["signal_id"] not in exclude]
    chosen = stratified_sample(signals, rng, size)
    rng.shuffle(chosen)
    sheet, key = [], []
    for index, (signal, stratum) in enumerate(chosen, start=1):
        item_id = f"{prefix}{index:03d}"
        sheet.append({"item_id": item_id, "date": signal["published_at"][:10], "source_type": source_type(signal), "text": signal["text"], "event_class": "", "sentiment": "", "notes": ""})
        key.append({"item_id": item_id, "signal_id": signal["signal_id"], "stratum": stratum})
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    write_rows(EVAL_DIR / f"labels_{window}_{split}_sheet.csv", SHEET_FIELDS, sheet)
    write_rows(EVAL_DIR / f"labels_{window}_{split}_key.csv", ["item_id", "signal_id", "stratum"], key)
    print(f"{window} {split} sheet {len(sheet)} items -> {EVAL_DIR}")


def legacy_w1_test() -> None:
    rng = random.Random(SEED)
    signals = [s for s in read_jsonl(PROCESSED_DIR / "w1" / "signals_v1.jsonl.gz") if s["text"]]
    chosen = stratified_sample(signals, rng)
    chosen += oversample(signals, {s["signal_id"] for s, _ in chosen}, rng)
    rng.shuffle(chosen)
    sheet, key = [], []
    for index, (signal, stratum) in enumerate(chosen, start=1):
        item_id = f"L{index:03d}"
        sheet.append({"item_id": item_id, "date": signal["published_at"][:10], "source_type": source_type(signal), "text": signal["text"], "event_class": "", "sentiment": "", "notes": ""})
        key.append({"item_id": item_id, "signal_id": signal["signal_id"], "stratum": stratum})
    relabel = rng.sample(sheet, RELABEL_SIZE)
    relabel_sheet, relabel_key = [], []
    for index, row in enumerate(relabel, start=1):
        relabel_sheet.append({**row, "item_id": f"R{index:02d}"})
        relabel_key.append({"relabel_id": f"R{index:02d}", "item_id": row["item_id"]})
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    write_rows(EVAL_DIR / "labels_sheet.csv", SHEET_FIELDS, sheet)
    write_rows(EVAL_DIR / "labels_key.csv", ["item_id", "signal_id", "stratum"], key)
    write_rows(EVAL_DIR / "relabel_sheet.csv", SHEET_FIELDS, relabel_sheet)
    write_rows(EVAL_DIR / "relabel_key.csv", ["relabel_id", "item_id"], relabel_key)
    print(f"label sheet {len(sheet)} items, relabel sheet {len(relabel_sheet)} items -> {EVAL_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--size", type=int, default=STRATIFIED_TOTAL)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--prefix", default="X")
    parser.add_argument("--exclude", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    if args.window is None:
        legacy_w1_test()
        return
    split_sheet(args.window, args.split, args.size, args.seed, args.prefix, read_existing_keys(args.exclude))


if __name__ == "__main__":
    main()
