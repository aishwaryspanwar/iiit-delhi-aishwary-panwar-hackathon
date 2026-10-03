import hashlib

from src.riskengine.models import CleanDoc, RawDoc
from src.riskengine.normalize import clean_text, hash_key


def text_hash(text: str) -> str:
    return hashlib.sha1(hash_key(text).encode("utf-8")).hexdigest()


def clean_and_dedup(docs: list[RawDoc]) -> list[CleanDoc]:
    unique: dict[str, CleanDoc] = {}
    for doc in sorted(docs, key=lambda d: (d.published_at, d.source, d.source_id)):
        text = clean_text(doc.text)
        if not hash_key(text):
            continue
        key = text_hash(text)
        if key in unique:
            kept = unique[key]
            kept.duplicate_count += 1
            if doc.outlet:
                kept.outlets.add(doc.outlet)
            kept.sources.add(doc.source)
            continue
        unique[key] = CleanDoc(
            source=doc.source,
            source_id=doc.source_id,
            published_at=doc.published_at,
            text=text,
            text_hash=key,
            url=doc.url,
            outlet=doc.outlet,
            outlets={doc.outlet} if doc.outlet else set(),
            sources={doc.source},
        )
    return list(unique.values())
