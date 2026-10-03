from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawDoc:
    source: str
    source_id: str
    published_at: datetime
    text: str
    url: str | None = None
    outlet: str | None = None


@dataclass
class CleanDoc:
    source: str
    source_id: str
    published_at: datetime
    text: str
    text_hash: str
    url: str | None
    outlet: str | None
    duplicate_count: int = 1
    outlets: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Entity:
    id: str
    name: str
    type: str
    ticker: str | None
    sector: str | None
    country: str | None
    importance: float
    matched: str


@dataclass(frozen=True)
class SentimentResult:
    score: float
    label: str
    model: str


@dataclass(frozen=True)
class EventResult:
    event_class: str
    confidence: float
    matched_rules: tuple[str, ...]
    runner_up: str | None
