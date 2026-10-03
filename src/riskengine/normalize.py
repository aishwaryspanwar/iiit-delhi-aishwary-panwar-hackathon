import html
import re
import unicodedata
from functools import lru_cache

from src.riskengine.config import load_yaml

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HANDLE_PATTERN = re.compile(r"(?<![\w$])@\w{1,30}")
TAG_PATTERN = re.compile(r"<[^>]{0,200}>")
CONTROL_PATTERN = re.compile(r"[\u0000-\u0008\u000b-\u001f\u007f�]")
WHITESPACE_PATTERN = re.compile(r"\s+")
HASH_STRIP_PATTERN = re.compile(r"[^a-z0-9]+")


@lru_cache(maxsize=1)
def outlet_suffix_pattern() -> re.Pattern[str]:
    suffixes = load_yaml("normalization.yaml")["outlet_suffixes"]
    alternatives = "|".join(re.escape(s) for s in sorted(suffixes, key=len, reverse=True))
    return re.compile(rf"\s*[-|–—:]\s*(?:{alternatives})\s*$", re.IGNORECASE)


def clean_text(text: str) -> str:
    max_length = load_yaml("normalization.yaml")["max_length"]
    value = unicodedata.normalize("NFKC", html.unescape(text or ""))
    value = TAG_PATTERN.sub(" ", value)
    value = URL_PATTERN.sub(" ", value)
    value = HANDLE_PATTERN.sub("@user", value)
    value = CONTROL_PATTERN.sub("", value)
    value = WHITESPACE_PATTERN.sub(" ", value).strip()
    value = outlet_suffix_pattern().sub("", value).strip()
    return value[:max_length]


def hash_key(text: str) -> str:
    return HASH_STRIP_PATTERN.sub(" ", text.lower()).strip()
