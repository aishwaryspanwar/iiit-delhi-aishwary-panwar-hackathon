import json

from src.api import service
from src.riskengine.config import REPO_ROOT

FIXTURE_DIR = REPO_ROOT / "frontend" / "src" / "test" / "fixtures"
DATASET = "stub"
PAGE_SIZE = 50


def write(name: str, payload) -> None:
    (FIXTURE_DIR / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8", newline="\n")


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    signals = service.signals(DATASET, {"limit": [str(PAGE_SIZE)]})
    stress = service.stress(DATASET)
    first_run = stress["runs"][0]["cluster_id"]
    payloads = {
        "meta": service.meta(),
        "datasets": [d for d in service.datasets() if d["id"] == DATASET],
        "summary": service.summary(DATASET),
        "events": service.events(DATASET),
        "signals": signals,
        "signal": service.signal_detail(DATASET, signals["items"][0]["signal_id"]),
        "stress": stress,
        "stressRun": service.stress_detail(DATASET, first_run),
        "alerts": service.alerts(DATASET),
        "geo": service.geo(DATASET, {}),
    }
    for name, payload in payloads.items():
        write(name, payload)
    print(f"wrote {len(payloads)} fixtures to {FIXTURE_DIR}")


if __name__ == "__main__":
    main()
