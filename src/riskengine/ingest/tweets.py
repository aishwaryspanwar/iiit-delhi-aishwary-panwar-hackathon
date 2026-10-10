import csv
from datetime import datetime
from pathlib import Path

from src.riskengine.config import DATA_DIR
from src.riskengine.models import RawDoc

def tweets_source_path(window: str) -> Path:
    return DATA_DIR / "sources" / window / "tweets.csv"


TWEETS_SOURCE_PATH = tweets_source_path("w1")
FIELDS = ["source_id", "published_at", "text"]


def read_tweet_documents(path: Path = TWEETS_SOURCE_PATH) -> list[RawDoc]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            RawDoc(
                source="kaggle_tweets",
                source_id=row["source_id"],
                published_at=datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")),
                text=row["text"],
            )
            for row in csv.DictReader(handle)
        ]
