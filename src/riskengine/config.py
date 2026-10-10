import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
ENGINE_VERSION = "0.2.0"


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict[str, Any]:
    with (CONFIG_DIR / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=None)
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(CONFIG_DIR / name, dtype=str, keep_default_na=False, encoding="utf-8")


def config_hash() -> str:
    digest = hashlib.sha1()
    for path in sorted(CONFIG_DIR.glob("*")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]
