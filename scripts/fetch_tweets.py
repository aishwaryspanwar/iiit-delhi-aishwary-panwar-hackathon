import argparse
import csv
from pathlib import Path

import pandas as pd

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.ingest.tweets import FIELDS, TWEETS_SOURCE_PATH
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
    args = parser.parse_args()
    tweets = window_tweets(args.raw, settings["window"]["start"], settings["window"]["end"])
    TWEETS_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tweets.to_csv(TWEETS_SOURCE_PATH, index=False, lineterminator="\n", encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    print(f"tweets={len(tweets)} -> {TWEETS_SOURCE_PATH}")


if __name__ == "__main__":
    main()
