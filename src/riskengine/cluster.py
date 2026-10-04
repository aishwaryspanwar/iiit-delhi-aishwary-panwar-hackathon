from collections import defaultdict
from datetime import date, timedelta

from src.riskengine.config import load_yaml
from src.riskengine.impact import baseline_mentions, cluster_components, cluster_impact, rubric


def cluster_key(signal: dict) -> tuple[str, str, str, str]:
    targets = signal["scope_targets"]
    return (
        signal["published_at"][:10],
        signal["event"]["class"],
        signal["scope"],
        targets[0] if targets else "none",
    )


def cluster_id_for(key: tuple[str, str, str, str]) -> str:
    day, event_class, scope, target = key
    return f"{day}|{event_class}|{scope}|{target}"


def trailing_history(key: tuple[str, str, str, str], mentions_by_key: dict[tuple[str, str, str, str], int]) -> list[int]:
    day = date.fromisoformat(key[0])
    days = rubric()["cluster"]["baseline_days"]
    history = []
    for offset in range(1, days + 1):
        previous = ((day - timedelta(days=offset)).isoformat(),) + key[1:]
        if previous in mentions_by_key:
            history.append(mentions_by_key[previous])
    return history


def consensus_targets(primary: str, members: list[dict], event_class: str) -> list[str]:
    if event_class in load_yaml("taxonomy_rules.yaml")["primary_target_only_classes"]:
        return [primary] if primary != "none" else []
    min_share = rubric()["cluster"]["target_min_share"]
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for index, member in enumerate(members):
        for target in set(member["scope_targets"]):
            counts[target] = counts.get(target, 0) + 1
            first_seen.setdefault(target, index)
    kept = [t for t in counts if t != primary and counts[t] / len(members) >= min_share]
    kept.sort(key=lambda t: (-counts[t], first_seen[t], t))
    return ([primary] if primary != "none" else []) + kept


def build_events(signals: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for signal in signals:
        key = cluster_key(signal)
        signal["cluster_id"] = cluster_id_for(key)
        groups[key].append(signal)
    mentions_by_key = {key: sum(m["duplicate_count"] for m in members) for key, members in groups.items()}
    first_day = date.fromisoformat(min(key[0] for key in groups)) if groups else None
    warmup_days = rubric()["cluster"]["warmup_days"]
    events = []
    for key, members in sorted(groups.items()):
        outlets = sorted({o for m in members for o in m["outlets"]})
        sources = sorted({s for m in members for s in m["sources"]})
        n_mentions = mentions_by_key[key]
        baseline = baseline_mentions(trailing_history(key, mentions_by_key))
        components = cluster_components([m["impact"]["score"] for m in members], len(outlets), n_mentions, baseline)
        ranked = sorted(members, key=lambda m: (-m["impact"]["score"], m["published_at"], m["signal_id"]))
        events.append({
            "schema_version": "1.0",
            "cluster_id": cluster_id_for(key),
            "class": key[1],
            "scope": key[2],
            "scope_targets": consensus_targets(key[3], members, key[1]),
            "t_start": min(m["published_at"] for m in members),
            "t_end": max(m["published_at"] for m in members),
            "n_items": len(members),
            "n_mentions": n_mentions,
            "n_sources": len(sources),
            "n_outlets": len(outlets),
            "sources": sources,
            "sentiment_mean": round(sum(m["sentiment"]["score"] for m in members) / len(members), 4),
            "confidence_mean": round(sum(m["event"]["confidence"] for m in members) / len(members), 4),
            "baseline_mentions": baseline,
            "warmup": (date.fromisoformat(key[0]) - first_day).days < warmup_days,
            "impact_components": components,
            "impact": cluster_impact(components),
            "representative_signal_ids": [m["signal_id"] for m in ranked[:3]],
        })
    return events
