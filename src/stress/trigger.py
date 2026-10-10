from datetime import datetime

from src.stress.shocks import shock_config

CHECK_LABELS = {
    "stress_class": "Event class is stress-relevant",
    "impact_above_threshold": "Event impact above threshold",
    "confidence_ok": "Classification confidence high enough",
    "not_positive": "News is not positive",
    "corroborated": "Corroborated by enough news outlets",
    "baseline_ready": "Baseline established",
    "cooldown": "Outside cooldown of a recent trigger",
}
EVENT_STATUS_LABELS = {
    "below": "Below threshold",
    "triggered": "Triggered stress test",
    "blocked": "Above threshold, blocked",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def condition_checks(event: dict, settings: dict) -> dict[str, bool]:
    return {
        "stress_class": event["class"] in settings["stress_classes"],
        "impact_above_threshold": event["impact"] > settings["impact_threshold"],
        "confidence_ok": event["confidence_mean"] >= settings["min_confidence"],
        "not_positive": event["sentiment_mean"] <= settings["max_sentiment"],
        "corroborated": event["n_outlets"] >= settings["min_news_outlets"],
        "baseline_ready": not event.get("warmup", False),
    }


def cooldown_key(event: dict) -> str:
    return event["class"]


def evaluate_triggers(events: list[dict]) -> list[dict]:
    settings = shock_config()["trigger"]
    last_fired: dict[str, tuple[datetime, float]] = {}
    decisions = []
    for event in sorted(events, key=lambda e: (e["t_start"], e["cluster_id"])):
        checks = condition_checks(event, settings)
        failed = [name for name, passed in checks.items() if not passed]
        key = cooldown_key(event)
        started = parse_time(event["t_start"])
        if not failed and key in last_fired:
            fired_at, fired_impact = last_fired[key]
            within = (started - fired_at).total_seconds() < settings["cooldown_hours"] * 3600
            if within and event["impact"] < fired_impact + settings["rearm_impact_delta"]:
                failed.append("cooldown")
        triggered = not failed
        if triggered:
            last_fired[key] = (started, event["impact"])
        decisions.append({
            "cluster_id": event["cluster_id"],
            "triggered": triggered,
            "checks": checks,
            "failed": failed,
        })
    return decisions


def event_status(event, triggered_ids: set[str], threshold: float) -> str:
    if event["cluster_id"] in triggered_ids:
        return "triggered"
    return "blocked" if event["impact"] > threshold else "below"
