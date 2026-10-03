import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src.app.data import DATASET_LABELS, available_datasets
from src.app.views import feed, stress, try_headline

st.set_page_config(page_title="Event-Driven Risk Engine", layout="wide")
st.title("Event-Driven Risk Engine → Portfolio Stress Testing")
st.caption("Unstructured news and social text → structured risk signals (sentiment, event class, impact) → event-triggered stress test of a synthetic wholesale-banking book.")

datasets = available_datasets()
if not datasets:
    st.error("No processed data found. Run: python -m src.pipeline --dataset stub")
    st.stop()
dataset = st.sidebar.selectbox("Dataset", datasets, format_func=DATASET_LABELS.get)
st.sidebar.caption("All views run on precomputed files in data/processed — no network, model or GPU needed at runtime.")

feed_tab, stress_tab, try_tab = st.tabs(["Signal feed", "Stress test", "Try a headline"])
with feed_tab:
    feed.render(dataset)
with stress_tab:
    stress.render(dataset)
with try_tab:
    try_headline.render()
