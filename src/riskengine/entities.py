import re
from dataclasses import dataclass
from functools import lru_cache

from src.riskengine.config import load_csv, load_yaml
from src.riskengine.models import Entity

SCOPE_BY_TYPE = {
    "company": "single_name",
    "sector": "sector",
    "commodity": "sector",
    "country": "country",
    "central_bank": "macro",
    "index": "macro",
}
CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


TOKEN_PATTERN = re.compile(r"\w+")


@dataclass(frozen=True)
class AliasMatcher:
    pattern: re.Pattern[str]
    entity_id: str
    token: str


@lru_cache(maxsize=1)
def entity_table() -> dict[str, dict[str, str]]:
    return {row["id"]: row for row in load_csv("entities.csv").to_dict("records")}


@lru_cache(maxsize=1)
def ticker_index() -> dict[str, str]:
    return {row["ticker"]: entity_id for entity_id, row in entity_table().items() if row["ticker"]}


@lru_cache(maxsize=1)
def alias_matchers() -> tuple[AliasMatcher, ...]:
    pairs = []
    for entity_id, row in entity_table().items():
        flags = 0 if row["case_sensitive"] == "true" else re.IGNORECASE
        for alias in filter(None, (a.strip() for a in row["aliases"].split("|"))):
            pattern = re.compile(rf"(?<![\w$]){re.escape(alias)}(?![\w])", flags)
            pairs.append((len(alias), alias, AliasMatcher(pattern, entity_id, first_token(alias))))
    pairs.sort(key=lambda item: (-item[0], item[1]))
    return tuple(matcher for _, _, matcher in pairs)


@lru_cache(maxsize=1)
def blocked_patterns() -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in load_yaml("taxonomy_rules.yaml").get("entity_alias_blocklist", []))


def first_token(alias: str) -> str:
    match = TOKEN_PATTERN.search(alias)
    return match.group(0).lower() if match else ""


def candidate_matchers(text: str) -> list[AliasMatcher]:
    tokens = {t.lower() for t in TOKEN_PATTERN.findall(text)}
    return [m for m in alias_matchers() if m.token in tokens]


def to_entity(entity_id: str, matched: str) -> Entity:
    row = entity_table()[entity_id]
    return Entity(
        id=entity_id,
        name=row["name"],
        type=row["type"],
        ticker=row["ticker"] or None,
        sector=row["sector"] or None,
        country=row["country"] or None,
        importance=float(row["importance"]),
        matched=matched,
    )


def overlaps(span: tuple[int, int], taken: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in taken)


def tag_entities(text: str) -> list[Entity]:
    taken: list[tuple[int, int]] = [match.span() for pattern in blocked_patterns() for match in pattern.finditer(text)]
    found: dict[str, tuple[int, str]] = {}
    for match in CASHTAG_PATTERN.finditer(text):
        entity_id = ticker_index().get(match.group(1))
        if entity_id:
            taken.append(match.span())
            found.setdefault(entity_id, (match.start(), match.group(0)))
    for matcher in candidate_matchers(text):
        for match in matcher.pattern.finditer(text):
            if overlaps(match.span(), taken):
                continue
            taken.append(match.span())
            found.setdefault(matcher.entity_id, (match.start(), match.group(0)))
    entities = [to_entity(entity_id, matched) for entity_id, (_, matched) in found.items()]
    position = {entity_id: start for entity_id, (start, _) in found.items()}
    return sorted(entities, key=lambda e: (-e.importance, position[e.id], e.id))


def scope_settings() -> tuple[dict[str, list[str]], set[str]]:
    taxonomy = load_yaml("taxonomy_rules.yaml")
    return taxonomy["scope_precedence"], set(taxonomy["actor_countries"])


def drop_actor_countries(entities: list[Entity], actors: set[str]) -> list[Entity]:
    has_target_country = any(e.type == "country" and e.id not in actors for e in entities)
    if not has_target_country:
        return entities
    return [e for e in entities if e.id not in actors]


def resolve_scope(entities: list[Entity], event_class: str = "other") -> tuple[str, list[str]]:
    precedence_by_class, actors = scope_settings()
    candidates = drop_actor_countries(entities, actors)
    if not candidates:
        return "none", []
    precedence = precedence_by_class.get(event_class, precedence_by_class["default"])
    present = {SCOPE_BY_TYPE[e.type] for e in candidates}
    scope = next(s for s in precedence if s in present)
    primary = [e.id for e in candidates if SCOPE_BY_TYPE[e.type] == scope]
    others = [e.id for e in candidates if SCOPE_BY_TYPE[e.type] != scope]
    return scope, primary + others
