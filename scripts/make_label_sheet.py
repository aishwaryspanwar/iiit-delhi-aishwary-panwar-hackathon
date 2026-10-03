import csv
import random
from collections import defaultdict
from datetime import date

from src.riskengine.config import DATA_DIR, PROCESSED_DIR
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


def stratified_sample(signals: list[dict], rng: random.Random) -> list[tuple[dict, str]]:
    strata: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for signal in signals:
        strata[(source_type(signal), iso_week(signal["published_at"]))].append(signal)
    picked = []
    for kind, share in (("news", NEWS_SHARE), ("tweet", 1 - NEWS_SHARE)):
        keys = sorted(k for k in strata if k[0] == kind)
        quota = round(STRATIFIED_TOTAL * share)
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


def main() -> None:
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


if __name__ == "__main__":
    main()
