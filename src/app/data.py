from pathlib import Path

import pandas as pd
import streamlit as st

from src.riskengine.config import PROCESSED_DIR
from src.riskengine.events import class_display_name
from src.riskengine.io import read_json, read_jsonl

DATASET_LABELS = {"w1": "W1 · Feb–Mar 2022 (GDELT + tweets)", "stub": "Stub sample (hand-written)"}


def available_datasets() -> list[str]:
    return [name for name in DATASET_LABELS if (PROCESSED_DIR / name / "signals_v1.jsonl.gz").exists()]


def dataset_dir(name: str) -> Path:
    return PROCESSED_DIR / name


@st.cache_data(show_spinner=False)
def load_signals(name: str) -> pd.DataFrame:
    records = read_jsonl(dataset_dir(name) / "signals_v1.jsonl.gz")
    rows = []
    for record in records:
        rows.append({
            "published_at": pd.Timestamp(record["published_at"]),
            "source": record["source"],
            "outlet": record["outlet"] or "",
            "text": record["text"] or "",
            "event_class": class_display_name(record["event"]["class"]),
            "confidence": record["event"]["confidence"],
            "rules": ", ".join(record["event"]["matched_rules"]),
            "sentiment": record["sentiment"]["score"],
            "impact": record["impact"]["score"],
            "scope": record["scope"],
            "targets": ", ".join(record["scope_targets"][:3]),
            "mentions": record["duplicate_count"],
            "cluster_id": record["cluster_id"],
            "signal_id": record["signal_id"],
        })
    return pd.DataFrame(rows).sort_values("published_at").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_events(name: str) -> pd.DataFrame:
    records = read_jsonl(dataset_dir(name) / "events_v1.jsonl.gz")
    frame = pd.DataFrame(records)
    frame["t_start"] = pd.to_datetime(frame["t_start"])
    frame["class_name"] = frame["class"].map(class_display_name)
    return frame


@st.cache_data(show_spinner=False)
def load_stress(name: str) -> dict:
    return read_json(dataset_dir(name) / "stress_results_v1.json")
