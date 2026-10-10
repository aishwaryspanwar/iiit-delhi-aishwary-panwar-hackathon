import argparse
import csv
import random

from src.riskengine.config import DATA_DIR

EVAL_DIR = DATA_DIR / "eval"
SEED = 20224
TEST_SHEETS = {"w1": "labels_sheet.csv", "w3": "labels_w3_test_sheet.csv"}
STAGE_A_PER_WINDOW = 25
STAGE_A_PATH = EVAL_DIR / "human_verify_stage_a.csv"
STAGE_B_PATH = EVAL_DIR / "human_verify_stage_b.csv"
STAGE_A_FIELDS = ["verify_id", "window", "item_id", "source_type", "text", "event_class", "sentiment", "notes"]
STAGE_B_FIELDS = ["verify_id", "window", "item_id", "source_type", "text", "llm_event_class", "llm_sentiment", "event_class", "sentiment", "notes"]


def read_rows(name: str) -> list[dict]:
    with (EVAL_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, fields, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def stage_a_items() -> dict[str, set[str]]:
    rng = random.Random(SEED)
    chosen = {}
    for window, sheet in sorted(TEST_SHEETS.items()):
        ids = sorted(row["item_id"] for row in read_rows(sheet))
        chosen[window] = set(rng.sample(ids, STAGE_A_PER_WINDOW))
    return chosen


def build_stage_a() -> None:
    chosen = stage_a_items()
    rows = []
    for window, sheet in sorted(TEST_SHEETS.items()):
        for row in read_rows(sheet):
            if row["item_id"] in chosen[window]:
                rows.append({"window": window, "item_id": row["item_id"], "source_type": row["source_type"], "text": row["text"], "event_class": "", "sentiment": "", "notes": ""})
    random.Random(SEED + 1).shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["verify_id"] = f"A{index:02d}"
    write_rows(STAGE_A_PATH, STAGE_A_FIELDS, rows)
    print(f"stage A {len(rows)} blind items -> {STAGE_A_PATH}")


def build_stage_b() -> None:
    chosen = stage_a_items()
    rows = []
    for window, sheet in sorted(TEST_SHEETS.items()):
        for row in read_rows(sheet):
            if row["item_id"] in chosen[window]:
                continue
            if not row["event_class"] or not row["sentiment"]:
                raise ValueError(f"{sheet} {row['item_id']} has no LLM label yet")
            rows.append({
                "window": window, "item_id": row["item_id"], "source_type": row["source_type"], "text": row["text"],
                "llm_event_class": row["event_class"], "llm_sentiment": row["sentiment"],
                "event_class": row["event_class"], "sentiment": row["sentiment"], "notes": "",
            })
    random.Random(SEED + 2).shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["verify_id"] = f"B{index:03d}"
    write_rows(STAGE_B_PATH, STAGE_B_FIELDS, rows)
    print(f"stage B {len(rows)} items to confirm or correct -> {STAGE_B_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["a", "b"], required=True)
    args = parser.parse_args()
    build_stage_a() if args.stage == "a" else build_stage_b()


if __name__ == "__main__":
    main()
