import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.ingest.gdelt import FIELDS, filter_gkg_rows, gdelt_source_path


def cache_dir(window: str) -> Path:
    return DATA_DIR / "raw" / f"gdelt_{window}"


def hourly_stamps(start: str, end: str, minute: int) -> list[str]:
    current = datetime.fromisoformat(start).replace(minute=minute)
    stop = datetime.fromisoformat(end) + timedelta(days=1)
    stamps = []
    while current < stop:
        stamps.append(current.strftime("%Y%m%d%H%M%S"))
        current += timedelta(hours=1)
    return stamps


def fetch_slot(stamp: str, url_template: str, cache: Path) -> tuple[str, int, str]:
    cache_path = cache / f"{stamp}.json"
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


def consolidate(stamps: list[str], cache: Path, output: Path) -> int:
    rows: dict[str, dict] = {}
    for stamp in stamps:
        path = cache / f"{stamp}.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                rows.setdefault(row["source_id"], row)
    ordered = sorted(rows.values(), key=lambda r: (r["published_at"], r["source_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    return len(ordered)


def main() -> None:
    settings = load_yaml("ingestion.yaml")
    window, gdelt = settings["window"], settings["gdelt"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", default=window["name"])
    parser.add_argument("--start", default=window["start"])
    parser.add_argument("--end", default=window["end"])
    args = parser.parse_args()
    stamps = hourly_stamps(args.start, args.end, gdelt["slot_minute"])
    cache = cache_dir(args.window)
    output = gdelt_source_path(args.window)
    cache.mkdir(parents=True, exist_ok=True)
    failures = []
    with ThreadPoolExecutor(max_workers=gdelt["workers"]) as pool:
        futures = [pool.submit(fetch_slot, stamp, gdelt["base_url"], cache) for stamp in stamps]
        for done, future in enumerate(as_completed(futures), start=1):
            stamp, count, status = future.result()
            if status.startswith("failed"):
                failures.append(stamp)
            if done % 50 == 0 or status.startswith("failed"):
                print(f"{done}/{len(stamps)} {stamp} {count} {status}", flush=True)
    total = consolidate(stamps, cache, output)
    print(f"slots={len(stamps)} failed={len(failures)} headlines={total} -> {output}")
    if failures:
        print("rerun to retry failed slots:", ",".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
