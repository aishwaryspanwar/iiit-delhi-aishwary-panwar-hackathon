from dataclasses import dataclass, field
from datetime import datetime

from src.stress.shocks import shock_config

CHECK_LABELS = {
    "stress_class": "Event class is stress-relevant",
    "impact_above_threshold": "Event impact above threshold",
    "confidence_ok": "Classification confidence high enough",
    "not_positive": "News is not positive",
    "direction_ok": "Not a positive credit action (upgrade)",
    "corroborated": "Corroborated by enough news outlets",
    "enough_mentions": "Enough mentions (estimated full feed)",
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


def condition_checks(state: dict, settings: dict) -> dict[str, bool]:
    return {
        "stress_class": state["class"] in settings["stress_classes"],
        "impact_above_threshold": state["impact"] > settings["impact_threshold"],
        "confidence_ok": state["confidence_mean"] >= settings["min_confidence"],
        "not_positive": state["sentiment_mean"] <= settings["max_sentiment"],
        "direction_ok": state.get("positive_share", 0.0) <= settings["max_positive_share"],
        "corroborated": state["n_outlets"] >= settings["min_news_outlets"],
        "enough_mentions": state.get("n_mentions_est", state.get("n_mentions", 0)) >= settings["min_mentions"],
        "baseline_ready": not state.get("warmup", False),
    }


def cooldown_key(event_class: str, targets: list[str]) -> tuple[str, str]:
    return event_class, targets[0] if targets else "none"


@dataclass
class CooldownTracker:
    hours: float
    rearm_delta: float
    last_fired: dict[tuple[str, str], tuple[datetime, float]] = field(default_factory=dict)

    @classmethod
    def from_config(cls) -> "CooldownTracker":
        settings = shock_config()["trigger"]
        return cls(settings["cooldown_hours"], settings["rearm_impact_delta"])

    def allows(self, key: tuple[str, str], at: datetime, impact: float) -> bool:
        if key not in self.last_fired:
            return True
        fired_at, fired_impact = self.last_fired[key]
        within = (at - fired_at).total_seconds() < self.hours * 3600
        return not within or impact >= fired_impact + self.rearm_delta

    def fire(self, key: tuple[str, str], at: datetime, impact: float) -> None:
        self.last_fired[key] = (at, impact)


def event_status(event, triggered_ids: set[str], threshold: float) -> str:
    if event["cluster_id"] in triggered_ids:
        return "triggered"
    return "blocked" if event["impact"] > threshold else "below"
