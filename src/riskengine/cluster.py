from collections import defaultdict

from src.riskengine.impact import cluster_impact


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


def build_events(signals: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for signal in signals:
        key = cluster_key(signal)
        signal["cluster_id"] = cluster_id_for(key)
        groups[key].append(signal)
    events = []
    for key, members in sorted(groups.items()):
        outlets = sorted({o for m in members for o in m["outlets"]})
        sources = sorted({s for m in members for s in m["sources"]})
        aggregate, breadth, impact = cluster_impact([m["impact"]["score"] for m in members], len(outlets))
        ranked = sorted(members, key=lambda m: (-m["impact"]["score"], m["published_at"], m["signal_id"]))
        targets = []
        for member in members:
            for target in member["scope_targets"]:
                if target not in targets:
                    targets.append(target)
        events.append({
            "schema_version": "1.0",
            "cluster_id": cluster_id_for(key),
            "class": key[1],
            "scope": key[2],
            "scope_targets": targets,
            "t_start": min(m["published_at"] for m in members),
            "t_end": max(m["published_at"] for m in members),
            "n_items": len(members),
            "n_mentions": sum(m["duplicate_count"] for m in members),
            "n_sources": len(sources),
            "n_outlets": len(outlets),
            "sources": sources,
            "sentiment_mean": round(sum(m["sentiment"]["score"] for m in members) / len(members), 4),
            "confidence_mean": round(sum(m["event"]["confidence"] for m in members) / len(members), 4),
            "item_impact_agg": aggregate,
            "breadth_term": breadth,
            "impact": impact,
            "representative_signal_ids": [m["signal_id"] for m in ranked[:3]],
        })
    return events
