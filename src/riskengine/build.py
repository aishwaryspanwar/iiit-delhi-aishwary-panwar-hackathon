import hashlib
from datetime import datetime, timezone

from src.riskengine.cluster import build_events
from src.riskengine.config import ENGINE_VERSION, config_hash
from src.riskengine.dedup import clean_and_dedup
from src.riskengine.entities import resolve_scope, tag_entities
from src.riskengine.events import classify
from src.riskengine.impact import impact_components, item_impact, rubric
from src.riskengine.models import CleanDoc, RawDoc
from src.riskengine.sentiment.base import SentimentModel


def signal_id_for(source: str, source_id: str) -> str:
    return hashlib.sha1(f"{source}:{source_id}".encode("utf-8")).hexdigest()[:16]


def build_id_for(docs: list[CleanDoc], model_name: str) -> str:
    digest = hashlib.sha1(f"{ENGINE_VERSION}|{config_hash()}|{model_name}".encode("utf-8"))
    for doc in docs:
        digest.update(doc.text_hash.encode("utf-8"))
    return digest.hexdigest()[:12]


def to_signal(doc: CleanDoc, sentiment, build: dict) -> dict:
    entities = tag_entities(doc.text)
    event = classify(doc.text)
    scope, targets = resolve_scope(entities, event.event_class)
    components = impact_components(event.event_class, sentiment.score, entities, doc.text)
    return {
        "schema_version": "1.0",
        "signal_id": signal_id_for(doc.source, doc.source_id),
        "source": doc.source,
        "source_id": doc.source_id,
        "url": doc.url,
        "outlet": doc.outlet,
        "outlets": sorted(doc.outlets),
        "sources": sorted(doc.sources),
        "duplicate_count": doc.duplicate_count,
        "published_at": doc.published_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "text": doc.text,
        "text_hash": doc.text_hash,
        "lang": "en",
        "entities": [
            {"id": e.id, "name": e.name, "type": e.type, "ticker": e.ticker, "matched": e.matched}
            for e in entities
        ],
        "scope": scope,
        "scope_targets": targets,
        "sentiment": {"score": sentiment.score, "label": sentiment.label, "model": sentiment.model},
        "event": {
            "class": event.event_class,
            "confidence": event.confidence,
            "matched_rules": list(event.matched_rules),
            "runner_up": event.runner_up,
        },
        "impact": {
            "score": item_impact(components),
            "components": components,
            "weights_version": rubric()["weights_version"],
        },
        "cluster_id": None,
        "build": build,
    }


def run_engine(raw_docs: list[RawDoc], model: SentimentModel) -> tuple[list[dict], list[dict]]:
    docs = clean_and_dedup(raw_docs)
    build = {"build_id": build_id_for(docs, model.name), "engine_version": ENGINE_VERSION, "config_hash": config_hash()}
    sentiments = model.score([d.text for d in docs])
    signals = [to_signal(doc, sentiment, build) for doc, sentiment in zip(docs, sentiments)]
    events = build_events(signals)
    return signals, events


def score_single_text(text: str, model: SentimentModel, source: str = "user_input") -> dict:
    doc = RawDoc(source=source, source_id=hashlib.sha1(text.encode("utf-8")).hexdigest()[:12], published_at=datetime.now(timezone.utc).replace(microsecond=0), text=text)
    signals, events = run_engine([doc], model)
    if not signals:
        raise ValueError("Text is empty after cleaning")
    return {"signal": signals[0], "event": events[0]}
