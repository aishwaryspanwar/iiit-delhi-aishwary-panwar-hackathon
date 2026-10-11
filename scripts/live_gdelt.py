import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from scripts.fetch_gdelt import fetch_slot
from src.pipeline import LIVE_DATASET, output_dir, write_outputs
from src.riskengine.build import run_engine
from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.ingest.gdelt import FIELDS
from src.riskengine.models import RawDoc
from src.riskengine.sentiment.loader import load_live_model

LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
LIVE_DIR = output_dir(LIVE_DATASET)
CACHE_DIR = DATA_DIR / "raw" / "gdelt_live"
STATE_PATH = LIVE_DIR / "state.json"
HEADLINES_PATH = LIVE_DIR / "headlines.csv"
STAMP_FORMAT = "%Y%m%d%H%M%S"
HISTORY_DAYS = 8
BACKFILL_HOURS = 168
POLL_SECONDS = 900
MIN_SLEEP_SECONDS = 60
SLOT = timedelta(minutes=15)
HOUR = timedelta(hours=1)
SAMPLED_SOURCE = "gdelt_gkg"
FULL_SOURCE = "gdelt_live"


def parse_stamp(value: str) -> datetime:
    return datetime.strptime(value, STAMP_FORMAT).replace(tzinfo=timezone.utc)


def format_stamp(moment: datetime) -> str:
    return moment.strftime(STAMP_FORMAT)


def latest_slot() -> datetime:
    lines = requests.get(LAST_UPDATE_URL, timeout=30).text.splitlines()
    url = next(line.split()[-1] for line in lines if line.endswith(".gkg.csv.zip"))
    return parse_stamp(url.rsplit("/", 1)[-1][:14])


def read_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}


def write_state(state: dict) -> None:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def plan_slots(latest: datetime, live_since: datetime, backfill_hours: int) -> list[tuple[str, str]]:
    horizon = latest - timedelta(days=HISTORY_DAYS)
    slots = []
    moment = live_since - backfill_hours * HOUR
    while moment < live_since:
        if moment >= horizon:
            slots.append((format_stamp(moment), SAMPLED_SOURCE))
        moment += HOUR
    moment = live_since
    while moment <= latest:
        if moment >= horizon:
            slots.append((format_stamp(moment), FULL_SOURCE))
        moment += SLOT
    return slots


def fetch_all(stamps: list[str]) -> list[str]:
    settings = load_yaml("ingestion.yaml")["gdelt"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=settings["workers"]) as pool:
        results = list(pool.map(lambda stamp: fetch_slot(stamp, settings["base_url"], CACHE_DIR), stamps))
    return [stamp for stamp, _, status in results if status.startswith("failed")]


def prune_cache(keep: set[str]) -> None:
    for path in CACHE_DIR.glob("*.json"):
        if path.stem not in keep:
            path.unlink()


def collect_rows(slots: list[tuple[str, str]]) -> list[dict]:
    rows: dict[str, dict] = {}
    for stamp, source in slots:
        path = CACHE_DIR / f"{stamp}.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                rows.setdefault(row["source_id"], {**row, "source": source})
    return sorted(rows.values(), key=lambda r: (r["published_at"], r["source_id"]))


def write_headlines(rows: list[dict]) -> None:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    with HEADLINES_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS + ["source"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def to_docs(rows: list[dict]) -> list[RawDoc]:
    return [
        RawDoc(source=r["source"], source_id=r["source_id"], published_at=datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")), text=r["title"], url=r["url"] or None, outlet=r["outlet"] or None)
        for r in rows
    ]


def poll_once(model, reset: bool, backfill_hours: int) -> dict:
    latest = latest_slot()
    state = read_state()
    if reset or "live_since" not in state:
        state = {"live_since": format_stamp(latest.replace(minute=0, second=0)), "backfill_hours": backfill_hours}
        write_state(state)
    slots = plan_slots(latest, parse_stamp(state["live_since"]), state["backfill_hours"])
    failed = fetch_all([stamp for stamp, _ in slots])
    prune_cache({stamp for stamp, _ in slots})
    rows = collect_rows(slots)
    write_headlines(rows)
    signals, stream = run_engine(to_docs(rows), model)
    results = write_outputs(LIVE_DIR, signals, stream)
    return {
        "latest_file": format_stamp(latest),
        "files": len(slots),
        "failed_files": len(failed),
        "headlines": len(rows),
        "events": len(stream.events),
        "alerts": len(stream.alerts),
        "stress_tests": len(results["runs"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll the GDELT feed, score it and stress the book on every alert.")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    parser.add_argument("--reset", action="store_true", help="discard the live state and backfill again")
    parser.add_argument("--backfill-hours", type=int, default=BACKFILL_HOURS, help="hours of history fetched on the first poll (hourly files)")
    args = parser.parse_args()
    model = load_live_model()
    print(f"sentiment model: {model.name}", flush=True)
    reset = args.reset
    while True:
        started = time.monotonic()
        try:
            print(datetime.now(timezone.utc).strftime("%H:%M:%SZ"), poll_once(model, reset, args.backfill_hours), flush=True)
        except requests.RequestException as error:
            print(f"poll failed: {error}", flush=True)
            if args.once:
                sys.exit(1)
        reset = False
        if args.once:
            return
        time.sleep(max(MIN_SLEEP_SECONDS, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
