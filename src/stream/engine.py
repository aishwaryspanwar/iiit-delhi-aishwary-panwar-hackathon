from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from src.riskengine.config import load_yaml
from src.riskengine.impact import baseline_mentions, cluster_components, cluster_impact, rubric
from src.stress.shocks import shock_config
from src.stress.trigger import CooldownTracker, condition_checks, cooldown_key

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
Key = tuple[str, str, str]


@dataclass
class StreamResult:
    events: list[dict]
    alerts: list[dict]
    decisions: list[dict]


@lru_cache(maxsize=1)
def sampling_rates() -> dict[str, float]:
    return {k: float(v) for k, v in load_yaml("ingestion.yaml")["sampling_rate"].items()}


def estimated_mentions(signal: dict) -> float:
    rates = sampling_rates()
    return signal["duplicate_count"] / rates.get(signal["source"], rates["default"]) if "source" in signal else float(signal["duplicate_count"])


def hour_index(published_at: str) -> int:
    moment = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return int((moment - EPOCH).total_seconds() // 3600)


def hour_time(index: int) -> str:
    return (EPOCH + timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M:%SZ")


def stream_key(signal: dict) -> Key:
    targets = signal["scope_targets"]
    return signal["event"]["class"], signal["scope"], targets[0] if targets else "none"


def cluster_id_for(day: str, key: Key) -> str:
    return f"{day}|{key[0]}|{key[1]}|{key[2]}"


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


def positive_share(members: list[dict]) -> float:
    directional = [m for m in members if m["event"].get("direction", "neutral") != "neutral"]
    if not directional:
        return 0.0
    return sum(m["event"]["direction"] == "positive" for m in directional) / len(directional)


class KeySeries:
    def __init__(self, key: Key, members: list[dict], start: int, end: int):
        self.key = key
        self.members = sorted(members, key=lambda m: (m["_hour"], m["published_at"], m["signal_id"]))
        self.hours = [m["_hour"] for m in self.members]
        self.start = start
        prefix = [0.0] * (end - start + 2)
        for member in self.members:
            prefix[member["_hour"] - start + 1] += member["_mentions"]
        for index in range(1, len(prefix)):
            prefix[index] += prefix[index - 1]
        self.prefix = prefix

    def window_mentions(self, hour: int, window: int) -> float:
        high = hour - self.start + 1
        low = max(0, high - window)
        return self.prefix[high] - self.prefix[low] if high > 0 else 0.0

    def window_members(self, hour: int, window: int) -> list[dict]:
        return self.members[bisect_left(self.hours, hour - window + 1):bisect_right(self.hours, hour)]


def tick_state(series: KeySeries, hour: int, settings: dict) -> dict:
    window = settings["window_hours"]
    members = series.window_members(hour, window)
    history = []
    for day in range(1, settings["baseline_days"] + 1):
        past = hour - 24 * day
        if past - window + 1 >= series.start:
            history.append(series.window_mentions(past, window))
    mentions = series.window_mentions(hour, window)
    baseline = baseline_mentions(history)
    outlets = {o for m in members for o in m["outlets"]}
    components = cluster_components([m["impact"]["score"] for m in members], len(outlets), mentions, baseline)
    return {
        "hour": hour,
        "class": series.key[0],
        "members": members,
        "impact": cluster_impact(components),
        "impact_components": components,
        "baseline_mentions": round(baseline, 2),
        "n_mentions_est": round(mentions, 2),
        "n_outlets": len(outlets),
        "sentiment_mean": round(sum(m["sentiment"]["score"] for m in members) / len(members), 4),
        "confidence_mean": round(sum(m["event"]["confidence"] for m in members) / len(members), 4),
        "positive_share": round(positive_share(members), 4),
        "warmup": hour - series.start < settings["warmup_days"] * 24,
    }


def window_summary(state: dict) -> dict:
    return {k: state[k] for k in ("n_mentions_est", "n_outlets", "sentiment_mean", "confidence_mean", "positive_share", "baseline_mentions")}


def run_stream(signals: list[dict]) -> StreamResult:
    settings = rubric()["cluster"]
    trigger_settings = shock_config()["trigger"]
    if not signals:
        return StreamResult([], [], [])
    for signal in signals:
        signal["_hour"] = hour_index(signal["published_at"])
        signal["_mentions"] = estimated_mentions(signal)
    start = min(s["_hour"] for s in signals)
    end = max(s["_hour"] for s in signals)
    by_key: dict[Key, list[dict]] = defaultdict(list)
    by_day_key: dict[tuple[str, Key], list[dict]] = defaultdict(list)
    for signal in signals:
        key = stream_key(signal)
        day = signal["published_at"][:10]
        signal["cluster_id"] = cluster_id_for(day, key)
        by_key[key].append(signal)
        by_day_key[(day, key)].append(signal)
    states: dict[tuple[str, Key], list[dict]] = defaultdict(list)
    candidates = []
    for key, members in by_key.items():
        series = KeySeries(key, members, start, end)
        first_hour_by_day: dict[str, int] = {}
        for member in series.members:
            first_hour_by_day.setdefault(member["published_at"][:10], member["_hour"])
        for day, first_hour in first_hour_by_day.items():
            day_end = min(end, first_hour - first_hour % 24 + 23)
            for hour in range(first_hour, day_end + 1):
                state = tick_state(series, hour, settings)
                state["checks"] = condition_checks(state, trigger_settings)
                states[(day, key)].append(state)
                if all(state["checks"].values()):
                    candidates.append((hour, cluster_id_for(day, key), day, key, state))
    candidates.sort(key=lambda item: (item[0], item[1]))
    tracker = CooldownTracker.from_config()
    alerts, alert_by_event, cooldown_blocked = [], {}, set()
    for hour, cluster_id, day, key, state in candidates:
        if cluster_id in alert_by_event:
            continue
        targets = consensus_targets(key[2], state["members"], key[0])
        detected = EPOCH + timedelta(hours=hour + 1)
        ckey = cooldown_key(key[0], targets)
        if not tracker.allows(ckey, detected, state["impact"]):
            cooldown_blocked.add(cluster_id)
            continue
        tracker.fire(ckey, detected, state["impact"])
        alert = {
            "schema_version": "1.0",
            "alert_id": f"{cluster_id}@{hour_time(hour + 1)}",
            "cluster_id": cluster_id,
            "class": key[0],
            "scope": key[1],
            "scope_targets": targets,
            "detected_at": hour_time(hour + 1),
            "first_headline_at": min(m["published_at"] for m in state["members"] if m["published_at"][:10] == day),
            "day_end_at": f"{day}T23:59:59Z",
            "impact": state["impact"],
            "impact_components": state["impact_components"],
            "window": window_summary(state),
            "checks": state["checks"],
            "representative_signal_ids": [m["signal_id"] for m in sorted(state["members"], key=lambda m: (-m["impact"]["score"], m["published_at"], m["signal_id"]))[:3]],
        }
        alerts.append(alert)
        alert_by_event[cluster_id] = alert
    events, decisions = [], []
    for (day, key), members in sorted(by_day_key.items(), key=lambda item: cluster_id_for(item[0][0], item[0][1])):
        cluster_id = cluster_id_for(day, key)
        day_states = states[(day, key)]
        peak = max(day_states, key=lambda s: (s["impact"], -s["hour"]))
        alert = alert_by_event.get(cluster_id)
        decisive = next(s for s in day_states if s["hour"] + 1 == hour_index(alert["detected_at"])) if alert else peak
        failed = [name for name, passed in decisive["checks"].items() if not passed]
        if not alert and cluster_id in cooldown_blocked:
            failed.append("cooldown")
        ranked = sorted(members, key=lambda m: (-m["impact"]["score"], m["published_at"], m["signal_id"]))
        outlets = sorted({o for m in members for o in m["outlets"]})
        sources = sorted({s for m in members for s in m["sources"]})
        events.append({
            "schema_version": "1.1",
            "cluster_id": cluster_id,
            "class": key[0],
            "scope": key[1],
            "scope_targets": consensus_targets(key[2], members, key[0]),
            "t_start": min(m["published_at"] for m in members),
            "t_end": max(m["published_at"] for m in members),
            "n_items": len(members),
            "n_mentions": sum(m["duplicate_count"] for m in members),
            "n_sources": len(sources),
            "n_outlets": len(outlets),
            "sources": sources,
            "sentiment_mean": round(sum(m["sentiment"]["score"] for m in members) / len(members), 4),
            "confidence_mean": round(sum(m["event"]["confidence"] for m in members) / len(members), 4),
            "baseline_mentions": max(1.0, peak["baseline_mentions"]),
            "warmup": peak["warmup"],
            "impact_components": peak["impact_components"],
            "impact": peak["impact"],
            "peak_at": hour_time(peak["hour"] + 1),
            "window": window_summary(peak),
            "detected_at": alert["detected_at"] if alert else None,
            "representative_signal_ids": [m["signal_id"] for m in ranked[:3]],
        })
        decisions.append({
            "cluster_id": cluster_id,
            "triggered": alert is not None,
            "checks": decisive["checks"],
            "failed": failed,
            "detected_at": alert["detected_at"] if alert else None,
        })
    for signal in signals:
        signal.pop("_hour", None)
        signal.pop("_mentions", None)
    return StreamResult(events, alerts, decisions)
