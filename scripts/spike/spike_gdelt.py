import csv
import io
import json
import random
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests

csv.field_size_limit(2**31 - 1)

WINDOWS = {
    "W1": ("2022-02-10", "2022-03-24"),
    "W2": ("2022-04-25", "2022-05-25"),
    "W3": ("2022-09-10", "2022-09-30"),
}
SAMPLES_PER_WINDOW = 10
BASE_URL = "http://data.gdeltproject.org/gdeltv2/{stamp}.gkg.csv.zip"
TITLE_PATTERN = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)
FINANCE_THEME_PATTERN = re.compile(r"(ECON_|EPU_|SANCTION|WB_1104|WB_442|WB_1234|ENV_OIL|ENV_GAS|FNCACT|TAX_FNCACT_BANK|CENTRAL_BANK|BANKRUPTCY|DEBT)")
OUTLET_ALLOWLIST = {
    "reuters.com", "bloomberg.com", "cnbc.com", "ft.com", "wsj.com", "marketwatch.com", "finance.yahoo.com",
    "businessinsider.com", "forbes.com", "economist.com", "fxstreet.com", "investing.com", "seekingalpha.com",
    "barrons.com", "theguardian.com", "bbc.co.uk", "bbc.com", "apnews.com", "cnn.com", "nytimes.com",
    "washingtonpost.com", "foxbusiness.com", "economictimes.indiatimes.com", "livemint.com", "business-standard.com",
    "moneycontrol.com", "thehindubusinessline.com", "financialpost.com", "fortune.com", "axios.com", "politico.com",
    "aljazeera.com", "nasdaq.com", "zerohedge.com", "rttnews.com", "benzinga.com", "thestreet.com", "fool.com",
}
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "spike_gdelt.json"


def slot_stamps(start: str, end: str) -> list[str]:
    current = datetime.fromisoformat(start)
    stop = datetime.fromisoformat(end) + timedelta(days=1)
    stamps = []
    while current < stop:
        stamps.append(current.strftime("%Y%m%d%H%M%S"))
        current += timedelta(minutes=15)
    return stamps


def fetch_zip(stamp: str) -> tuple[bytes | None, float, int]:
    started = time.perf_counter()
    response = requests.get(BASE_URL.format(stamp=stamp), timeout=60)
    elapsed = time.perf_counter() - started
    if response.status_code != 200:
        return None, elapsed, response.status_code
    return response.content, elapsed, 200


def parse_rows(payload: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = archive.namelist()[0]
        text = archive.read(name).decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE))


def analyse_rows(rows: list[list[str]]) -> dict:
    total = 0
    with_title = 0
    finance_titles = set()
    allowlisted_titles = set()
    examples = []
    for row in rows:
        if len(row) < 27:
            continue
        total += 1
        match = TITLE_PATTERN.search(row[26])
        title = match.group(1).strip() if match else ""
        if not title:
            continue
        with_title += 1
        themes = row[7] + ";" + row[8]
        outlet = row[3].lower()
        normalized = re.sub(r"\W+", " ", title.lower()).strip()
        if FINANCE_THEME_PATTERN.search(themes):
            finance_titles.add(normalized)
            if outlet in OUTLET_ALLOWLIST:
                allowlisted_titles.add(normalized)
                if len(examples) < 400:
                    examples.append({"outlet": outlet, "title": title})
    return {
        "records": total,
        "with_title": with_title,
        "finance_unique_titles": len(finance_titles),
        "finance_allowlisted_unique_titles": len(allowlisted_titles),
        "examples": examples,
    }


def run_window(label: str, start: str, end: str, rng: random.Random) -> dict:
    stamps = slot_stamps(start, end)
    sample = sorted(rng.sample(stamps, SAMPLES_PER_WINDOW))
    results = []
    for stamp in sample:
        payload, elapsed, status = fetch_zip(stamp)
        entry = {"stamp": stamp, "status": status, "seconds": round(elapsed, 2)}
        if payload is not None:
            entry["zip_bytes"] = len(payload)
            entry.update(analyse_rows(parse_rows(payload)))
        results.append(entry)
        print(label, json.dumps({k: v for k, v in entry.items() if k != "examples"}), flush=True)
    ok = [r for r in results if r["status"] == 200]
    slots_per_day = 96
    days = len(stamps) / slots_per_day
    summary = {
        "window": label,
        "start": start,
        "end": end,
        "slots": len(stamps),
        "days": days,
        "sampled": len(results),
        "available": len(ok),
    }
    if ok:
        mean = lambda key: sum(r[key] for r in ok) / len(ok)
        summary.update({
            "mean_zip_mb": round(mean("zip_bytes") / 1e6, 2),
            "mean_seconds": round(mean("seconds"), 2),
            "title_rate": round(sum(r["with_title"] for r in ok) / max(1, sum(r["records"] for r in ok)), 3),
            "finance_titles_per_slot": round(mean("finance_unique_titles"), 1),
            "allowlisted_titles_per_slot": round(mean("finance_allowlisted_unique_titles"), 1),
            "est_finance_titles_per_day_upper": round(mean("finance_unique_titles") * slots_per_day, 0),
            "est_allowlisted_titles_per_day_upper": round(mean("finance_allowlisted_unique_titles") * slots_per_day, 0),
            "est_full_window_gb": round(mean("zip_bytes") * len(stamps) / 1e9, 1),
            "est_full_window_hours": round(mean("seconds") * len(stamps) / 3600, 1),
            "examples": [e for r in ok for e in r.get("examples", [])],
        })
    return {"summary": summary, "samples": results}


def main() -> None:
    rng = random.Random(20221)
    selected = sys.argv[1:] or list(WINDOWS)
    report = {label: run_window(label, *WINDOWS[label], rng) for label in selected}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for label, data in report.items():
        print(json.dumps(data["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
