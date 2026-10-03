import csv
from datetime import datetime
from pathlib import Path

from src.riskengine.config import DATA_DIR
from src.riskengine.models import RawDoc

STUB_PATH = DATA_DIR / "stub" / "stub_documents.csv"


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_stub_documents(path: Path = STUB_PATH) -> list[RawDoc]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            RawDoc(
                source=row["source"],
                source_id=row["source_id"],
                published_at=parse_utc(row["published_at"]),
                text=row["text"],
                url=row["url"] or None,
                outlet=row["outlet"] or None,
            )
            for row in csv.DictReader(handle)
        ]
