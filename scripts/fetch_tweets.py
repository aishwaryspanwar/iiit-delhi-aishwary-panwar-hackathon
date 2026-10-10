import argparse
import csv
from pathlib import Path

import pandas as pd

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.ingest.tweets import FIELDS, tweets_source_path
from src.riskengine.normalize import clean_text


def window_tweets(raw_path: Path, start: str, end: str) -> pd.DataFrame:
    frame = pd.read_csv(raw_path, encoding="utf-8", encoding_errors="replace")
    frame["row_number"] = range(len(frame))
    frame["timestamp"] = pd.to_datetime(frame["Date"], utc=True)
    end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    selected = frame[(frame["timestamp"] >= pd.Timestamp(start, tz="UTC")) & (frame["timestamp"] < end_exclusive)].copy()
    selected["text"] = selected["Tweet"].astype(str).map(clean_text)
    selected = selected[selected["text"].str.len() > 0]
    selected["source_id"] = "row-" + selected["row_number"].astype(str)
    selected["published_at"] = selected["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return selected.sort_values(["published_at", "row_number"])[FIELDS]


def main() -> None:
    settings = load_yaml("ingestion.yaml")
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DATA_DIR / "raw" / settings["tweets"]["raw_file"])
    parser.add_argument("--window", default=settings["window"]["name"])
    parser.add_argument("--start", default=settings["window"]["start"])
    parser.add_argument("--end", default=settings["window"]["end"])
    args = parser.parse_args()
    tweets = window_tweets(args.raw, args.start, args.end)
    output = tweets_source_path(args.window)
    output.parent.mkdir(parents=True, exist_ok=True)
    tweets.to_csv(output, index=False, lineterminator="\n", encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    print(f"tweets={len(tweets)} -> {output}")


if __name__ == "__main__":
    main()
