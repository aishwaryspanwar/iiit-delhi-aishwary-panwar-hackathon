import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.evaluate import CLASSES, EVAL_DIR, macro_f1, read_rows
from src.riskengine.config import REPO_ROOT

FREEZE_TAG = "eval-freeze"
SPLITS = {
    "W1 test": ("labels_sheet.csv", "labels_key.csv"),
    "W3 test": ("labels_w3_test_sheet.csv", "labels_w3_test_key.csv"),
}
PREDICT = """
import csv, json, sys
sys.path.insert(0, sys.argv[1])
from src.riskengine.events import classify
from src.riskengine.normalize import clean_text
with open(sys.argv[2], encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
print(json.dumps({row["item_id"]: classify(clean_text(row["text"])).event_class for row in rows}))
"""


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()


def frozen_predictions(checkout: Path, sheet: Path) -> dict[str, str]:
    result = subprocess.run([sys.executable, "-I", "-c", PREDICT, str(checkout), str(sheet)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def representative_rows(sheet: str, key: str) -> list[dict]:
    strata = {row["item_id"]: row["stratum"] for row in read_rows(EVAL_DIR / key)}
    return [row for row in read_rows(EVAL_DIR / sheet) if not strata[row["item_id"]].startswith("oversample")]


def verify(tag: str) -> dict[str, float]:
    scores = {}
    with tempfile.TemporaryDirectory() as folder:
        checkout = Path(folder) / "frozen"
        git("worktree", "add", "--detach", str(checkout), tag)
        try:
            for name, (sheet, key) in SPLITS.items():
                predicted = frozen_predictions(checkout, EVAL_DIR / sheet)
                rows = representative_rows(sheet, key)
                scores[name] = round(macro_f1([r["event_class"] for r in rows], [predicted[r["item_id"]] for r in rows], CLASSES), 2)
        finally:
            git("worktree", "remove", "--force", str(checkout))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score the test labels with the rules exactly as they stood at the freeze tag.")
    parser.add_argument("--tag", default=FREEZE_TAG)
    args = parser.parse_args()
    changed = git("diff", "--name-only", args.tag, "HEAD", "--", "config/").split()
    print(f"{args.tag} is commit {git('rev-list', '-n', '1', args.tag)[:7]}; config files changed since: {', '.join(changed) or 'none'}")
    for name, score in verify(args.tag).items():
        print(f"{name}: frozen event-class macro-F1 {score:.2f}")


if __name__ == "__main__":
    main()
