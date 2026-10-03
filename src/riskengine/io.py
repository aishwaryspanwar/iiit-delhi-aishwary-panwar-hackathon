import gzip
import io
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_records(records: list[dict], schema_name: str) -> None:
    checker = validator(schema_name)
    for index, record in enumerate(records):
        errors = sorted(checker.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            raise ValueError(f"{schema_name} record {index} invalid: {errors[0].message} at {list(errors[0].path)}")


def dumps(record: dict) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(dumps(record) + "\n" for record in records).encode("utf-8")
    if path.suffix == ".gz":
        buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as archive:
            archive.write(payload)
        payload = buffer.getvalue()
    path.write_bytes(payload)


def read_jsonl(path: Path) -> list[dict]:
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=1) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
