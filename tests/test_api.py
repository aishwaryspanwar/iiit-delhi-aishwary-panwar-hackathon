import gzip
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src.api import service
from src.api.server import create_server, static_file
from src.riskengine.config import PROCESSED_DIR
from src.riskengine.io import read_json, read_jsonl
from src.stress.trigger import EVENT_STATUS_LABELS, event_status
from src.stress.whatif import EXAMPLES, what_if_event

DATASET = "stub"
INVASION = "Russia launches full-scale invasion of Ukraine as explosions heard in Kyiv"


@pytest.fixture(scope="module")
def base_url():
    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def fetch(url: str, body: dict | None = None, headers: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST" if body is not None else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return response.status, json.loads(raw), response.headers
    except HTTPError as error:
        return error.code, json.loads(error.read()), error.headers


def test_health_and_datasets(base_url):
    status, payload, _ = fetch(f"{base_url}/api/health")
    assert status == 200 and payload["status"] == "ok"
    assert DATASET in payload["datasets"]
    status, datasets, _ = fetch(f"{base_url}/api/datasets")
    assert {"id": DATASET, "label": "Stub sample (hand-written)"} in datasets


def test_summary_matches_processed_files():
    folder = PROCESSED_DIR / DATASET
    signals = read_jsonl(folder / "signals_v1.jsonl.gz")
    events = read_jsonl(folder / "events_v1.jsonl.gz")
    stress = read_json(folder / "stress_results_v1.json")
    summary = service.summary(DATASET)
    assert summary["totals"] == {"signals": len(signals), "events": len(events), "triggered": len(stress["runs"]), "decisions": len(stress["decisions"])}
    assert sum(d["signals"] for d in summary["days"]) == len(signals)
    assert sum(d["events"] for d in summary["days"]) == len(events)
    assert sum(d["triggered"] for d in summary["days"]) == len(stress["runs"])
    assert [r["totals"] for r in summary["runs"]] == [r["totals"] for r in stress["runs"]]


def test_event_status_matches_streamlit_labels():
    stress = read_json(PROCESSED_DIR / DATASET / "stress_results_v1.json")
    triggered = {d["cluster_id"] for d in stress["decisions"] if d["triggered"]}
    rows = service.events(DATASET)
    assert {r["cluster_id"] for r in rows if r["status"] == "triggered"} == triggered
    for row in rows:
        assert row["status"] == event_status(row, triggered, stress["trigger_settings"]["impact_threshold"])
        assert EVENT_STATUS_LABELS[row["status"]]


def test_signal_filters_and_pagination(base_url):
    status, page, _ = fetch(f"{base_url}/api/datasets/{DATASET}/signals?limit=5")
    assert status == 200 and page["total"] == service.summary(DATASET)["totals"]["signals"] and len(page["items"]) == 5
    times = [s["published_at"] for s in page["items"]]
    assert times == sorted(times, reverse=True)
    status, filtered, _ = fetch(f"{base_url}/api/datasets/{DATASET}/signals?class=geopolitical&until=2022-02-24&min_impact=5&sort=impact")
    assert status == 200 and filtered["total"] > 0
    for signal in filtered["items"]:
        assert signal["event"]["class"] == "geopolitical"
        assert signal["published_at"][:10] <= "2022-02-24"
        assert signal["impact"]["score"] >= 5
    scores = [s["impact"]["score"] for s in filtered["items"]]
    assert scores == sorted(scores, reverse=True)
    status, searched, _ = fetch(f"{base_url}/api/datasets/{DATASET}/signals?q=KYIV")
    assert status == 200 and all("kyiv" in (s["text"] or "").lower() or "kyiv" in (s["outlet"] or "").lower() for s in searched["items"])


@pytest.mark.parametrize("query", ["limit=0", "limit=500", "offset=-1", "min_impact=11", "min_impact=nan", "until=24-02-2022", "sort=random", "q=" + "x" * 200])
def test_signal_query_validation(base_url, query):
    status, payload, _ = fetch(f"{base_url}/api/datasets/{DATASET}/signals?{query}")
    assert status == 400 and payload["error"]


def test_signal_and_event_detail_explain_cluster(base_url):
    stress = read_json(PROCESSED_DIR / DATASET / "stress_results_v1.json")
    cluster_id = stress["runs"][0]["cluster_id"]
    status, detail, _ = fetch(f"{base_url}/api/datasets/{DATASET}/events/{cluster_id.replace('|', '%7C')}")
    assert status == 200
    assert detail["event"]["status"] == "triggered" and detail["decision"]["triggered"]
    assert detail["run"]["totals"] == stress["runs"][0]["totals"]
    signal_id = detail["representative_signals"][0]["signal_id"]
    status, signal, _ = fetch(f"{base_url}/api/datasets/{DATASET}/signals/{signal_id}")
    assert status == 200 and signal["signal"]["signal_id"] == signal_id
    assert signal["cluster"]["event"]["cluster_id"] == cluster_id


def test_stress_detail_is_the_engine_output(base_url):
    stress = read_json(PROCESSED_DIR / DATASET / "stress_results_v1.json")
    run = stress["runs"][0]
    status, detail, _ = fetch(f"{base_url}/api/datasets/{DATASET}/stress/{run['cluster_id'].replace('|', '%7C')}")
    assert status == 200 and detail["run"] == run
    assert detail["base_scenario"]["rates_bp"] != 0
    status, overview, _ = fetch(f"{base_url}/api/datasets/{DATASET}/stress")
    assert status == 200 and len(overview["runs"]) == len(stress["runs"])


def test_alerts_are_the_stream_output_with_stress_pnl(base_url):
    alerts = read_jsonl(PROCESSED_DIR / DATASET / "alerts_v1.jsonl.gz")
    stress = read_json(PROCESSED_DIR / DATASET / "stress_results_v1.json")
    status, rows, _ = fetch(f"{base_url}/api/datasets/{DATASET}/alerts")
    assert status == 200 and [r["alert_id"] for r in rows] == [a["alert_id"] for a in alerts]
    pnl = {r["cluster_id"]: r["totals"]["pnl"] for r in stress["runs"]}
    assert all(r["pnl"] == pnl[r["cluster_id"]] for r in rows)


def test_entity_views_aggregate_signals(base_url):
    status, rows, _ = fetch(f"{base_url}/api/datasets/{DATASET}/entities")
    assert status == 200 and rows
    top = rows[0]
    status, detail, _ = fetch(f"{base_url}/api/datasets/{DATASET}/entities/{top['id'].replace(':', '%3A')}")
    assert status == 200 and detail["signals"] == top["signals"]
    assert sum(day["signals"] for day in detail["timeline"]) == top["signals"]


def test_evaluation_endpoint_serves_committed_files(base_url):
    status, payload, _ = fetch(f"{base_url}/api/evaluation")
    assert status == 200 and payload["metrics"] == read_json(PROCESSED_DIR.parent / "eval" / "metrics.json")


@pytest.mark.parametrize("path", [
    "/api/datasets/nope/summary",
    f"/api/datasets/{DATASET}/entities/company:NOPE",
    f"/api/datasets/{DATASET}/signals/0000000000000000",
    f"/api/datasets/{DATASET}/events/missing",
    f"/api/datasets/{DATASET}/stress/missing",
    "/api/unknown",
])
def test_not_found_is_json_without_traceback(base_url, path):
    status, payload, _ = fetch(f"{base_url}{path}")
    assert status == 404 and "Traceback" not in payload["error"]


def test_score_matches_streamlit_try_headline_flow(base_url):
    status, payload, _ = fetch(f"{base_url}/api/score", {"text": INVASION, "outlets": 25, "volume_multiple": 8.0})
    assert status == 200
    assert payload["signal"]["event"]["class"] == "geopolitical"
    assert payload["triggered"] is True
    assert payload["run"]["totals"]["pnl"] < 0
    expected = what_if_event({"signal": payload["signal"], "event": {**payload["event"]}}, 25, 8.0)
    assert payload["event"]["impact"] == expected["impact"]


def test_score_without_trigger_or_preview_has_no_run():
    payload = service.score({"text": EXAMPLES[4], "outlets": 1, "volume_multiple": 1.0})
    assert payload["triggered"] is False and payload["run"] is None


@pytest.mark.parametrize("body", [
    {"text": ""},
    {"text": "   "},
    {"text": "x" * 301},
    {"text": INVASION, "outlets": 0},
    {"text": INVASION, "outlets": 31},
    {"text": INVASION, "outlets": True},
    {"text": INVASION, "volume_multiple": 5.0},
    {"text": INVASION, "preview": "yes"},
    {"text": 42},
])
def test_score_rejects_invalid_input(base_url, body):
    status, payload, _ = fetch(f"{base_url}/api/score", body)
    assert status == 400 and payload["error"]


def test_score_rejects_non_json_and_wrong_method(base_url):
    request = Request(f"{base_url}/api/score", data=b"not json", headers={"Content-Type": "application/json"}, method="POST")
    with pytest.raises(HTTPError) as error:
        urlopen(request, timeout=30)
    assert error.value.code == 400
    status, payload, _ = fetch(f"{base_url}/api/score")
    assert status == 405


def test_large_responses_are_gzipped(base_url):
    status, events, headers = fetch(f"{base_url}/api/datasets/{DATASET}/events", headers={"Accept-Encoding": "gzip"})
    assert status == 200 and headers.get("Content-Encoding") == "gzip" and isinstance(events, list)


def test_static_files_cannot_escape_build_dir(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    (dist / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    assert static_file("/app.js", dist) == (dist / "app.js").resolve()
    assert static_file("/../secret.txt", dist) == dist.resolve() / "index.html"
    assert static_file("/%2e%2e/secret.txt", dist) == dist.resolve() / "index.html"
    assert static_file("/anything", tmp_path / "missing") is None
