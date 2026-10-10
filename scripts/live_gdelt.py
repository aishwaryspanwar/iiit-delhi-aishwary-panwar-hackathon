import argparse
import csv
import time
from datetime import datetime, timedelta, timezone

import requests

from src.riskengine.build import run_engine
from src.riskengine.config import DATA_DIR
from src.riskengine.ingest.gdelt import FIELDS, filter_gkg_rows
from src.riskengine.io import write_jsonl
from src.riskengine.models import RawDoc
from src.riskengine.sentiment.loader import load_live_model

LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
LIVE_DIR = DATA_DIR / "processed" / "live"
HEADLINES_PATH = LIVE_DIR / "headlines.csv"
HISTORY_DAYS = 8
POLL_SECONDS = 900


def latest_gkg_url() -> str:
    lines = requests.get(LAST_UPDATE_URL, timeout=30).text.splitlines()
    return next(line.split()[-1] for line in lines if line.endswith(".gkg.csv.zip"))


def read_headlines() -> dict[str, dict]:
    if not HEADLINES_PATH.exists():
        return {}
    with HEADLINES_PATH.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def write_headlines(rows: dict[str, dict]) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    kept = sorted((r for r in rows.values() if r["published_at"] >= cutoff), key=lambda r: (r["published_at"], r["source_id"]))
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    with HEADLINES_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)


def to_docs(rows: dict[str, dict]) -> list[RawDoc]:
    return [
        RawDoc(source="gdelt_live", source_id=r["source_id"], published_at=datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")), text=r["title"], url=r["url"] or None, outlet=r["outlet"] or None)
        for r in rows.values()
    ]


def poll_once(model) -> dict:
    url = latest_gkg_url()
    rows = read_headlines()
    for row in filter_gkg_rows(requests.get(url, timeout=120).content):
        rows.setdefault(row["source_id"], row)
    write_headlines(rows)
    signals, stream = run_engine(to_docs(read_headlines()), model)
    write_jsonl(LIVE_DIR / "signals_v1.jsonl.gz", signals)
    write_jsonl(LIVE_DIR / "events_v1.jsonl.gz", stream.events)
    write_jsonl(LIVE_DIR / "alerts_v1.jsonl.gz", stream.alerts)
    return {"file": url.rsplit("/", 1)[-1], "headlines": len(signals), "events": len(stream.events), "alerts": len(stream.alerts)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    model = load_live_model()
    while True:
        print(poll_once(model), flush=True)
        if args.once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
