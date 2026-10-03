import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.ingest.gdelt import FIELDS, GDELT_SOURCE_PATH, filter_gkg_rows

CACHE_DIR = DATA_DIR / "raw" / "gdelt_w1"


def hourly_stamps(start: str, end: str, minute: int) -> list[str]:
    current = datetime.fromisoformat(start).replace(minute=minute)
    stop = datetime.fromisoformat(end) + timedelta(days=1)
    stamps = []
    while current < stop:
        stamps.append(current.strftime("%Y%m%d%H%M%S"))
        current += timedelta(hours=1)
    return stamps


def fetch_slot(stamp: str, url_template: str) -> tuple[str, int, str]:
    cache_path = CACHE_DIR / f"{stamp}.json"
    if cache_path.exists():
        return stamp, len(json.loads(cache_path.read_text(encoding="utf-8"))), "cached"
    for attempt in range(3):
        try:
            response = requests.get(url_template.format(stamp=stamp), timeout=90)
            if response.status_code == 404:
                cache_path.write_text("[]", encoding="utf-8")
                return stamp, 0, "missing"
            response.raise_for_status()
            rows = filter_gkg_rows(response.content)
            cache_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            return stamp, len(rows), "downloaded"
        except (requests.RequestException, OSError) as error:
            if attempt == 2:
                return stamp, 0, f"failed: {error}"
            time.sleep(5 * (attempt + 1))
    return stamp, 0, "failed"


def consolidate(stamps: list[str]) -> int:
    rows: dict[str, dict] = {}
    for stamp in stamps:
        path = CACHE_DIR / f"{stamp}.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                rows.setdefault(row["source_id"], row)
    ordered = sorted(rows.values(), key=lambda r: (r["published_at"], r["source_id"]))
    GDELT_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GDELT_SOURCE_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    return len(ordered)


def main() -> None:
    settings = load_yaml("ingestion.yaml")
    window, gdelt = settings["window"], settings["gdelt"]
    stamps = hourly_stamps(window["start"], window["end"], gdelt["slot_minute"])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    with ThreadPoolExecutor(max_workers=gdelt["workers"]) as pool:
        futures = [pool.submit(fetch_slot, stamp, gdelt["base_url"]) for stamp in stamps]
        for done, future in enumerate(as_completed(futures), start=1):
            stamp, count, status = future.result()
            if status.startswith("failed"):
                failures.append(stamp)
            if done % 50 == 0 or status.startswith("failed"):
                print(f"{done}/{len(stamps)} {stamp} {count} {status}", flush=True)
    total = consolidate(stamps)
    print(f"slots={len(stamps)} failed={len(failures)} headlines={total} -> {GDELT_SOURCE_PATH}")
    if failures:
        print("rerun to retry failed slots:", ",".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
