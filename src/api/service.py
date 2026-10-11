import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from src.pipeline import DATASET_LABELS, LIVE_DATASET, available_datasets
from src.riskengine.build import score_single_text
from src.riskengine.config import ENGINE_VERSION, PROCESSED_DIR, load_yaml
from src.riskengine.entities import entity_table
from src.riskengine.events import taxonomy
from src.riskengine.io import read_json, read_jsonl
from src.riskengine.sentiment.loader import load_live_model
from src.stress.engine import run_stress
from src.stress.explain import scope_target_names
from src.stress.portfolio_gen import load_portfolio
from src.stress.shocks import shock_config
from src.stress.trigger import CHECK_LABELS, EVENT_STATUS_LABELS, condition_checks, event_status
from src.stress.whatif import EXAMPLES, MAX_LENGTH, OUTLET_RANGE, VOLUME_OPTIONS, what_if_event

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50
MAX_QUERY_LENGTH = 120
CLUSTER_SIGNAL_LIMIT = 25
SIGNAL_SORTS = ("time", "impact")
CACHED_VERSIONS = 16
GEO_ENTITY_TYPES = ("country", "central_bank", "index")
GEO_HEADLINES = 12
MAX_GEO_DAYS = 366


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


@dataclass(frozen=True)
class DatasetBundle:
    name: str
    signals: list[dict]
    signals_by_id: dict[str, dict]
    signals_by_cluster: dict[str, list[dict]]
    events: list[dict]
    events_by_id: dict[str, dict]
    stress: dict
    runs_by_id: dict[str, dict]
    decisions_by_id: dict[str, dict]
    status_by_id: dict[str, str]


def data_version(name: str) -> int:
    path = PROCESSED_DIR / name / "stress_results_v1.json"
    return path.stat().st_mtime_ns if path.exists() else 0


def updated_at(name: str) -> str | None:
    if name != LIVE_DATASET:
        return None
    version = data_version(name)
    return datetime.fromtimestamp(version / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if version else None


def bundle(name: str) -> DatasetBundle:
    if name not in available_datasets():
        raise NotFound(f"Dataset '{name}' is not available")
    return load_bundle(name, data_version(name))


@lru_cache(maxsize=CACHED_VERSIONS)
def load_bundle(name: str, version: int) -> DatasetBundle:
    folder = PROCESSED_DIR / name
    signals = sorted(read_jsonl(folder / "signals_v1.jsonl.gz"), key=lambda s: (s["published_at"], s["signal_id"]), reverse=True)
    events = sorted(read_jsonl(folder / "events_v1.jsonl.gz"), key=lambda e: (e["t_start"], e["cluster_id"]))
    stress = read_json(folder / "stress_results_v1.json")
    triggered = {d["cluster_id"] for d in stress["decisions"] if d["triggered"]}
    threshold = stress["trigger_settings"]["impact_threshold"]
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for signal in signals:
        if signal["cluster_id"]:
            by_cluster[signal["cluster_id"]].append(signal)
    return DatasetBundle(
        name=name,
        signals=signals,
        signals_by_id={s["signal_id"]: s for s in signals},
        signals_by_cluster=dict(by_cluster),
        events=events,
        events_by_id={e["cluster_id"]: e for e in events},
        stress=stress,
        runs_by_id={r["cluster_id"]: r for r in stress["runs"]},
        decisions_by_id={d["cluster_id"]: d for d in stress["decisions"]},
        status_by_id={e["cluster_id"]: event_status(e, triggered, threshold) for e in events},
    )


@lru_cache(maxsize=1)
def sentiment_model():
    return load_live_model()


def health() -> dict:
    return {"status": "ok", "engine_version": ENGINE_VERSION, "datasets": available_datasets()}


def datasets() -> list[dict]:
    return [{"id": name, "label": DATASET_LABELS[name], "live": name == LIVE_DATASET, "updated_at": updated_at(name)} for name in available_datasets()]


def meta() -> dict:
    rules = taxonomy()
    shocks = shock_config()
    impact = load_yaml("impact.yaml")
    return {
        "engine_version": ENGINE_VERSION,
        "classes": rules["classes"],
        "class_priority": rules["priority"],
        "rules": {r["id"]: {"class": r["class"], "weight": r["weight"], "patterns": r["patterns"]} for r in rules["rules"]},
        "entities": {k: {f: v[f] for f in ("name", "type", "ticker", "sector", "country")} for k, v in entity_table().items()},
        "impact_weights": impact["weights"],
        "cluster_weights": impact["cluster"]["weights"],
        "shocks_version": shocks["shocks_version"],
        "trigger_settings": shocks["trigger"],
        "severity": shocks["severity"],
        "scenarios": shocks["scenarios"],
        "check_labels": CHECK_LABELS,
        "status_labels": EVENT_STATUS_LABELS,
        "headline": {
            "max_length": MAX_LENGTH,
            "examples": EXAMPLES,
            "outlet_range": list(OUTLET_RANGE),
            "volume_options": VOLUME_OPTIONS,
            "sentiment_model": sentiment_model().name,
        },
    }


def lead_signal(data: DatasetBundle, event: dict) -> dict | None:
    for signal_id in event["representative_signal_ids"]:
        signal = data.signals_by_id.get(signal_id)
        if signal:
            return {k: signal[k] for k in ("signal_id", "text", "outlet", "source", "published_at", "url")}
    return None


def event_row(data: DatasetBundle, event: dict) -> dict:
    return {**event, "status": data.status_by_id[event["cluster_id"]], "lead": lead_signal(data, event)}


def run_summary(data: DatasetBundle, run: dict) -> dict:
    event = data.events_by_id.get(run["cluster_id"], {})
    return {
        "cluster_id": run["cluster_id"],
        "class": run["class"],
        "impact": run["impact"],
        "scope": run["scope"],
        "scope_targets": run["scope_targets"],
        "scope_label": scope_target_names(event) if event else ", ".join(run["scope_targets"]),
        "t_start": run["t_start"],
        "totals": run["totals"],
        "in_scope_positions": run["in_scope_positions"],
        "multiplier": run["shocks_applied"]["multiplier"],
        "lead": lead_signal(data, event) if event else None,
    }


def empty_day(day: str) -> dict:
    return {
        "date": day,
        "signals": 0,
        "mentions": 0,
        "sentiment_sum": 0.0,
        "by_class": {},
        "by_sentiment": {"neg": 0, "neu": 0, "pos": 0},
        "by_source": {},
        "events": 0,
        "above_threshold": 0,
        "triggered": 0,
        "max_event_impact": None,
    }


def summary(name: str) -> dict:
    bundle(name)
    return load_summary(name, data_version(name))


@lru_cache(maxsize=CACHED_VERSIONS)
def load_summary(name: str, version: int) -> dict:
    data = bundle(name)
    days: dict[str, dict] = {}
    for signal in data.signals:
        day = days.setdefault(signal["published_at"][:10], empty_day(signal["published_at"][:10]))
        day["signals"] += 1
        day["mentions"] += signal["duplicate_count"]
        day["sentiment_sum"] += signal["sentiment"]["score"]
        day["by_class"][signal["event"]["class"]] = day["by_class"].get(signal["event"]["class"], 0) + 1
        day["by_sentiment"][signal["sentiment"]["label"]] += 1
        day["by_source"][signal["source"]] = day["by_source"].get(signal["source"], 0) + 1
    for event in data.events:
        day = days.setdefault(event["t_start"][:10], empty_day(event["t_start"][:10]))
        status = data.status_by_id[event["cluster_id"]]
        day["events"] += 1
        day["above_threshold"] += status != "below"
        day["triggered"] += status == "triggered"
        day["max_event_impact"] = max(day["max_event_impact"] or 0.0, event["impact"])
    for day in days.values():
        day["sentiment_sum"] = round(day["sentiment_sum"], 4)
    failures = Counter(check for d in data.stress["decisions"] if not d["triggered"] for check in d["failed"])
    first = data.signals[-1] if data.signals else None
    return {
        "dataset": {"id": name, "label": DATASET_LABELS[name]},
        "live": name == LIVE_DATASET,
        "updated_at": updated_at(name),
        "build": first["build"] if first else None,
        "sentiment_models": sorted({s["sentiment"]["model"] for s in data.signals}),
        "sources": sorted({s["source"] for s in data.signals}),
        "classes": sorted({s["event"]["class"] for s in data.signals}),
        "scopes": sorted({s["scope"] for s in data.signals}),
        "totals": {"signals": len(data.signals), "events": len(data.events), "triggered": len(data.stress["runs"]), "decisions": len(data.stress["decisions"])},
        "days": [days[key] for key in sorted(days)],
        "trigger_settings": data.stress["trigger_settings"],
        "shocks_version": data.stress["shocks_version"],
        "decision_failures": dict(sorted(failures.items())),
        "runs": [run_summary(data, run) for run in data.stress["runs"]],
    }


def events(name: str) -> list[dict]:
    bundle(name)
    return load_events(name, data_version(name))


@lru_cache(maxsize=CACHED_VERSIONS)
def load_events(name: str, version: int) -> list[dict]:
    data = bundle(name)
    return [event_row(data, event) for event in data.events]


def event_detail(name: str, cluster_id: str) -> dict:
    data = bundle(name)
    event = data.events_by_id.get(cluster_id)
    if event is None:
        raise NotFound("Event cluster not found")
    members = sorted(data.signals_by_cluster.get(cluster_id, []), key=lambda s: (-s["impact"]["score"], s["signal_id"]))
    representatives = [data.signals_by_id[i] for i in event["representative_signal_ids"] if i in data.signals_by_id]
    run = data.runs_by_id.get(cluster_id)
    return {
        "event": event_row(data, event),
        "scope_label": scope_target_names(event),
        "decision": data.decisions_by_id.get(cluster_id),
        "representative_signals": representatives,
        "member_signals": members[:CLUSTER_SIGNAL_LIMIT],
        "member_count": len(members),
        "run": run_summary(data, run) if run else None,
        "scenario_defined": event["class"] in shock_config()["scenarios"],
    }


def split_values(params: dict[str, list[str]], key: str) -> set[str]:
    return {v for raw in params.get(key, []) for v in raw.split(",") if v}


def single(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[-1] if values else None


def parse_int(value: str | None, default: int, low: int, high: int, label: str) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except ValueError as error:
        raise BadRequest(f"'{label}' must be an integer") from error
    if not low <= number <= high:
        raise BadRequest(f"'{label}' must be between {low} and {high}")
    return number


def parse_float(value: str | None, default: float, low: float, high: float, label: str) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except ValueError as error:
        raise BadRequest(f"'{label}' must be a number") from error
    if not math.isfinite(number) or not low <= number <= high:
        raise BadRequest(f"'{label}' must be between {low:g} and {high:g}")
    return number


def parse_day(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) != 10 or value[4] != "-" or value[7] != "-" or not (value[:4] + value[5:7] + value[8:]).isdigit():
        raise BadRequest("'until' must be a date in YYYY-MM-DD format")
    return value


def signals(name: str, params: dict[str, list[str]]) -> dict:
    data = bundle(name)
    until = parse_day(single(params, "until"))
    classes = split_values(params, "class")
    sources = split_values(params, "source")
    sentiments = split_values(params, "sentiment")
    scopes = split_values(params, "scope")
    cluster = single(params, "cluster")
    min_impact = parse_float(single(params, "min_impact"), 1.0, 1.0, 10.0, "min_impact")
    query = (single(params, "q") or "").strip().lower()
    if len(query) > MAX_QUERY_LENGTH:
        raise BadRequest(f"'q' must be at most {MAX_QUERY_LENGTH} characters")
    sort = single(params, "sort") or "time"
    if sort not in SIGNAL_SORTS:
        raise BadRequest(f"'sort' must be one of {', '.join(SIGNAL_SORTS)}")
    offset = parse_int(single(params, "offset"), 0, 0, 10_000_000, "offset")
    limit = parse_int(single(params, "limit"), DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE, "limit")
    matches = []
    for signal in data.signals:
        if until and signal["published_at"][:10] > until:
            continue
        if classes and signal["event"]["class"] not in classes:
            continue
        if sources and signal["source"] not in sources:
            continue
        if sentiments and signal["sentiment"]["label"] not in sentiments:
            continue
        if scopes and signal["scope"] not in scopes:
            continue
        if cluster and signal["cluster_id"] != cluster:
            continue
        if signal["impact"]["score"] < min_impact:
            continue
        if query and query not in (signal["text"] or "").lower() and query not in (signal["outlet"] or "").lower():
            continue
        matches.append(signal)
    if sort == "impact":
        matches.sort(key=lambda s: -s["impact"]["score"])
    return {"total": len(matches), "offset": offset, "limit": limit, "items": matches[offset:offset + limit]}


def signal_detail(name: str, signal_id: str) -> dict:
    data = bundle(name)
    signal = data.signals_by_id.get(signal_id)
    if signal is None:
        raise NotFound("Signal not found")
    cluster_id = signal["cluster_id"]
    return {"signal": signal, "cluster": event_detail(name, cluster_id) if cluster_id in data.events_by_id else None}


def alerts(name: str) -> list[dict]:
    bundle(name)
    return load_alerts(name, data_version(name))


@lru_cache(maxsize=CACHED_VERSIONS)
def load_alerts(name: str, version: int) -> list[dict]:
    path = PROCESSED_DIR / name / "alerts_v1.jsonl.gz"
    data = bundle(name)
    rows = []
    for alert in (read_jsonl(path) if path.exists() else []):
        run = data.runs_by_id.get(alert["cluster_id"])
        event = data.events_by_id.get(alert["cluster_id"])
        rows.append({
            **alert,
            "scope_label": scope_target_names({**event, "scope_targets": alert["scope_targets"]}) if event else ", ".join(alert["scope_targets"]),
            "lead": lead_signal(data, {"representative_signal_ids": alert["representative_signal_ids"]}),
            "pnl": run["totals"]["pnl"] if run else None,
            "pnl_pct": run["totals"]["pnl_pct"] if run else None,
        })
    return rows


def signal_countries(signal: dict) -> list[str]:
    table = entity_table()
    codes = set()
    for entity in signal["entities"]:
        row = table.get(entity["id"], {})
        if row.get("type") in GEO_ENTITY_TYPES and row.get("country"):
            codes.add(row["country"])
    return sorted(codes)


def located_signals(name: str) -> list[tuple[dict, list[str]]]:
    bundle(name)
    return load_located_signals(name, data_version(name))


@lru_cache(maxsize=CACHED_VERSIONS)
def load_located_signals(name: str, version: int) -> list[tuple[dict, list[str]]]:
    located = [(signal, signal_countries(signal)) for signal in bundle(name).signals]
    return [(signal, codes) for signal, codes in located if codes]


def headline_row(signal: dict) -> dict:
    return {
        "signal_id": signal["signal_id"],
        "text": signal["text"],
        "outlet": signal["outlet"],
        "source": signal["source"],
        "published_at": signal["published_at"],
        "impact": signal["impact"]["score"],
        "sentiment": signal["sentiment"]["score"],
        "sentiment_label": signal["sentiment"]["label"],
        "class": signal["event"]["class"],
    }


def in_range(day_key: str, since: str | None, until: str | None) -> bool:
    return (not until or day_key <= until) and (not since or day_key >= since)


def country_row(code: str, members: list[dict]) -> dict:
    ranked = sorted(members, key=lambda s: (-s["impact"]["score"], s["published_at"], s["signal_id"]))
    by_class = Counter(s["event"]["class"] for s in members)
    return {
        "code": code,
        "signals": len(members),
        "mean_sentiment": round(sum(s["sentiment"]["score"] for s in members) / len(members), 4),
        "max_impact": ranked[0]["impact"]["score"],
        "top_class": by_class.most_common(1)[0][0],
        "by_class": dict(sorted(by_class.items())),
        "headlines": [headline_row(s) for s in ranked[:GEO_HEADLINES]],
    }


def geo(name: str, params: dict[str, list[str]]) -> dict:
    data = bundle(name)
    until = parse_day(single(params, "until"))
    days = parse_int(single(params, "days"), 0, 0, MAX_GEO_DAYS, "days")
    since = (date.fromisoformat(until) - timedelta(days=days - 1)).isoformat() if until and days else None
    in_period = [s for s in data.signals if in_range(s["published_at"][:10], since, until)]
    by_country: dict[str, list[dict]] = defaultdict(list)
    for signal, codes in located_signals(name):
        if in_range(signal["published_at"][:10], since, until):
            for code in codes:
                by_country[code].append(signal)
    countries = sorted((country_row(code, members) for code, members in by_country.items()), key=lambda c: (-c["signals"], c["code"]))
    return {
        "until": until,
        "since": since or (in_period[-1]["published_at"][:10] if in_period else None),
        "total_signals": len(in_period),
        "located_signals": len({s["signal_id"] for members in by_country.values() for s in members}),
        "countries": countries,
    }


def stress(name: str) -> dict:
    data = bundle(name)
    overview = summary(name)
    return {
        "trigger_settings": overview["trigger_settings"],
        "shocks_version": overview["shocks_version"],
        "decision_failures": overview["decision_failures"],
        "totals": overview["totals"],
        "above_threshold": sum(1 for status in data.status_by_id.values() if status != "below"),
        "runs": overview["runs"],
    }


def stress_detail(name: str, cluster_id: str) -> dict:
    data = bundle(name)
    run = data.runs_by_id.get(cluster_id)
    if run is None:
        raise NotFound("No stress test was triggered for this event")
    event = data.events_by_id[cluster_id]
    return {
        "run": run,
        "summary": run_summary(data, run),
        "event": event_row(data, event),
        "decision": data.decisions_by_id.get(cluster_id),
        "representative_signals": [data.signals_by_id[i] for i in event["representative_signal_ids"] if i in data.signals_by_id],
        "base_scenario": shock_config()["scenarios"].get(run["class"]),
        "trigger_settings": data.stress["trigger_settings"],
    }


def score(body: object) -> dict:
    if not isinstance(body, dict):
        raise BadRequest("Request body must be a JSON object")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise BadRequest("Enter a headline to score")
    if len(text) > MAX_LENGTH:
        raise BadRequest(f"Text must be at most {MAX_LENGTH} characters")
    outlets = body.get("outlets", OUTLET_RANGE[0])
    if isinstance(outlets, bool) or not isinstance(outlets, int) or not OUTLET_RANGE[0] <= outlets <= OUTLET_RANGE[1]:
        raise BadRequest(f"'outlets' must be an integer between {OUTLET_RANGE[0]} and {OUTLET_RANGE[1]}")
    volume = body.get("volume_multiple", VOLUME_OPTIONS[0])
    if isinstance(volume, bool) or not isinstance(volume, (int, float)) or float(volume) not in VOLUME_OPTIONS:
        raise BadRequest("'volume_multiple' must be one of the offered options")
    preview = body.get("preview", False)
    if not isinstance(preview, bool):
        raise BadRequest("'preview' must be true or false")
    try:
        result = score_single_text(text, sentiment_model())
    except ValueError as error:
        raise BadRequest("Nothing left to score after cleaning (links and handles are removed)") from error
    event = what_if_event(result, outlets, float(volume))
    checks = condition_checks(event, shock_config()["trigger"])
    triggered = all(checks.values())
    scenario_defined = event["class"] in shock_config()["scenarios"]
    run = None
    if (triggered or preview) and scenario_defined:
        run = run_stress(load_portfolio(), event, {result["signal"]["signal_id"]: result["signal"]})
    return {
        "signal": result["signal"],
        "event": event,
        "scope_label": scope_target_names(event),
        "checks": checks,
        "triggered": triggered,
        "scenario_defined": scenario_defined,
        "run": run,
    }
