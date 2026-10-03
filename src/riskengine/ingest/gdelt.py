import csv
import io
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.models import RawDoc

csv.field_size_limit(2**31 - 1)

GDELT_SOURCE_PATH = DATA_DIR / "sources" / "w1" / "gdelt_headlines.csv"
TITLE_PATTERN = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)
FIELDS = ["source_id", "published_at", "outlet", "url", "title"]


def ingestion_settings() -> dict:
    return load_yaml("ingestion.yaml")


def theme_pattern() -> re.Pattern[str]:
    return re.compile("|".join(re.escape(t) for t in ingestion_settings()["gdelt"]["theme_prefixes"]))


def parse_gkg_date(value: str) -> str:
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def filter_gkg_rows(payload: bytes) -> list[dict]:
    settings = ingestion_settings()["gdelt"]
    allowlist = set(settings["outlet_allowlist"])
    themes = theme_pattern()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read(archive.namelist()[0]).decode("utf-8", errors="replace")
    kept = []
    for row in csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(row) < 27 or row[3].lower() not in allowlist:
            continue
        match = TITLE_PATTERN.search(row[26])
        title = match.group(1).strip() if match else ""
        if len(title) < settings["min_title_length"] or not themes.search(row[7] + ";" + row[8]):
            continue
        kept.append({
            "source_id": row[0],
            "published_at": parse_gkg_date(row[1]),
            "outlet": row[3].lower(),
            "url": row[4],
            "title": title,
        })
    return kept


def read_gdelt_documents(path: Path = GDELT_SOURCE_PATH) -> list[RawDoc]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            RawDoc(
                source="gdelt_gkg",
                source_id=row["source_id"],
                published_at=datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")),
                text=row["title"],
                url=row["url"] or None,
                outlet=row["outlet"] or None,
            )
            for row in csv.DictReader(handle)
        ]
