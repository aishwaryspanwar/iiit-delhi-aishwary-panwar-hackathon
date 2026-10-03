from datetime import datetime

from src.stress.shocks import shock_config


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def condition_checks(event: dict, settings: dict) -> dict[str, bool]:
    return {
        "stress_class": event["class"] in settings["stress_classes"],
        "impact_above_threshold": event["impact"] > settings["impact_threshold"],
        "confidence_ok": event["confidence_mean"] >= settings["min_confidence"],
        "not_positive": event["sentiment_mean"] <= settings["max_sentiment"],
    }


def cooldown_key(event: dict) -> tuple[str, str]:
    targets = event["scope_targets"]
    return event["class"], targets[0] if targets else "none"


def evaluate_triggers(events: list[dict]) -> list[dict]:
    settings = shock_config()["trigger"]
    last_fired: dict[tuple[str, str], tuple[datetime, float]] = {}
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
