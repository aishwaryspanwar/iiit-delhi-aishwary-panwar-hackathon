import os
import shutil
from datetime import datetime, timezone

import pytest

import src.pipeline as pipeline
from scripts.live_gdelt import FULL_SOURCE, SAMPLED_SOURCE, plan_slots
from src.api import service
from src.riskengine.config import PROCESSED_DIR
from src.riskengine.io import read_json, write_json

UTC = timezone.utc


def test_backfill_is_hourly_and_live_slots_are_quarter_hourly():
    live_since = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
    latest = datetime(2026, 10, 10, 12, 45, tzinfo=UTC)
    slots = plan_slots(latest, live_since, 3)
    assert slots == [
        ("20261010090000", SAMPLED_SOURCE),
        ("20261010100000", SAMPLED_SOURCE),
        ("20261010110000", SAMPLED_SOURCE),
        ("20261010120000", FULL_SOURCE),
        ("20261010121500", FULL_SOURCE),
        ("20261010123000", FULL_SOURCE),
        ("20261010124500", FULL_SOURCE),
    ]


def test_slots_older_than_the_history_window_are_dropped():
    live_since = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
    latest = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)
    slots = plan_slots(latest, live_since, 48)
    assert all(source == FULL_SOURCE for _, source in slots)
    assert slots[0][0] == "20261002000000" and slots[-1][0] == "20261010000000"


@pytest.fixture
def live_copy(tmp_path, monkeypatch):
    shutil.copytree(PROCESSED_DIR / "stub", tmp_path / pipeline.LIVE_DATASET)
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(service, "PROCESSED_DIR", tmp_path)
    return tmp_path / pipeline.LIVE_DATASET


def test_live_dataset_is_listed_and_reloads_when_its_files_change(live_copy):
    listed = {d["id"]: d for d in service.datasets()}
    assert listed[pipeline.LIVE_DATASET]["live"] is True and listed[pipeline.LIVE_DATASET]["updated_at"]
    before = service.summary(pipeline.LIVE_DATASET)
    assert before["live"] is True and before["totals"]["triggered"] > 0
    stress_path = live_copy / "stress_results_v1.json"
    results = read_json(stress_path)
    results["runs"] = []
    write_json(stress_path, results)
    stamp = os.stat(stress_path).st_mtime_ns + 5_000_000_000
    os.utime(stress_path, ns=(stamp, stamp))
    after = service.summary(pipeline.LIVE_DATASET)
    assert after["totals"]["triggered"] == 0
    assert service.alerts(pipeline.LIVE_DATASET)[0]["pnl"] is None


def test_incomplete_dataset_is_not_listed(live_copy):
    (live_copy / "stress_results_v1.json").unlink()
    assert pipeline.LIVE_DATASET not in pipeline.available_datasets()
