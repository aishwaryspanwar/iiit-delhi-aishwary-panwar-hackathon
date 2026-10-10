# Event-Driven Risk Engine & Portfolio Stress Testing - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Aishwary S Panwar
**College Email ID:** aishwary23055@iiitd.ac.in
**College / Campus:** IIIT Delhi
**Demo Video Link:** _to be added_
**Slide Deck Link (if hosted externally):** not hosted externally — the deck will be committed as `docs/presentation.pdf`

## 1. Project Overview / Problem Statement & Approach

**Problem.** News and social posts move markets before any risk system sees a number. The brief asks for an NLP engine that turns unstructured text from at least two sources into structured signals (sentiment in [-1, 1], an event class and a 1–10 impact score), exposed through a file or API, plus at least one downstream consumer.

**What this project does.**
1. **Risk engine.** Reads GDELT news headlines and stock tweets, cleans and de-duplicates them, tags entities, classifies each item into one of nine event classes, scores sentiment and impact, and groups related items into event clusters.
2. **Module B: event-triggered portfolio stress test (the downstream consumer).** When a cluster is severe, well corroborated and negative, it triggers a stress test of a synthetic wholesale-banking book and reports portfolio value before and after, with P&L attributed by asset class and risk factor.

**Approach, in one line:** every number is traceable. The engine is rule-based, deterministic and explainable, with no LLM in the scoring path, and it runs offline on a CPU.

| Stage | How it works |
|---|---|
| Clean and de-duplicate | Strip HTML, links and handles; exact-hash dedup, keeping the duplicate count and outlets so breadth survives |
| Entities and scope | 115 known entities and cashtags (companies, countries, sectors, commodities, central banks) decide whether an event is single-name, sector, country or macro |
| Event class | 27 weighted regex rules across 9 classes; confidence = rule share × strength |
| Sentiment | VADER with a finance lexicon (build default). FinBERT scores are produced offline for evaluation only |
| Item impact | `1 + 9 × (0.35·class prior + 0.25·sentiment magnitude + 0.20·entity importance + 0.20·severity cues)`, all components stored |
| Cluster impact | Clusters keyed by day, class, scope and primary target: `1 + 9 × (0.5·severity + 0.2·breadth + 0.3·abnormal volume)`. Abnormal volume compares mentions with the previous 7 days only (no look-ahead). Calibration notes: [docs/impact_calibration.md](docs/impact_calibration.md) |
| Stress trigger | Stress-relevant class, impact > 7, confidence ≥ 0.6, sentiment ≤ 0.1, at least 2 outlets, baseline established, with a 72-hour cooldown per class |
| Valuation | Scope-aware shocks scaled by a severity multiplier; bonds use separate rate and spread duration plus convexity, loans take the change in expected loss, swaps use signed DV01, equities use beta, and options use delta, gamma and vega. P&L attribution by factor sums exactly to the total |

## 2. Architecture & Tech Stack

```
 GDELT headlines ─┐                                      config/*.yaml, entities.csv
 Stock tweets ────┤                                                │
                  ▼                                                ▼
          ┌───────────────┐   signals_v1.jsonl.gz     ┌────────────────────────┐
          │  Risk engine  │ ─ events_v1.jsonl.gz ───▶ │  Module B stress test  │
          │ src/riskengine│   (validated schemas)     │       src/stress       │
          └───────────────┘                           └───────────┬────────────┘
                                                                  │ stress_results_v1.json
                       data/processed/<dataset>/  ◀───────────────┘
                                   │
              ┌────────────────────┴─────────────────────┐
              ▼                                          ▼
   Streamlit reference app                  Read-only JSON API (src/api)
     src/app, port 8501                      port 8000 ──▶ React app (frontend/)
```

- **Precompute plus a thin runtime.** `python -m src.pipeline` writes versioned, schema-validated files; both frontends only read them. Output is deterministic (sorted keys, no wall-clock values), and tests check that the committed files are current.
- **Signals are exposed as files and as an API.** The JSONL schemas in `src/riskengine/schema/` are the contract; `python -m src.api` serves the same data as JSON.
- **Two frontends, one engine.** Streamlit is the reference UI. React is a more polished UI that calls the same Python code through the API and never re-implements scoring or valuation.
- **Stack:** Python 3.13, pandas, numpy, PyYAML, jsonschema, vaderSentiment, Streamlit, Plotly; React 19, TypeScript, Vite, Tailwind CSS, Recharts. Build-time only: PyTorch and transformers (FinBERT), yfinance.

| Path | Contents |
|---|---|
| `src/riskengine/` | Cleaning, dedup, entities, event rules, sentiment, impact, clustering, schemas |
| `src/stress/` | Portfolio generator, shocks, valuation, triggers, explanations |
| `src/pipeline.py` | Builds a dataset end to end |
| `src/app/` | Streamlit dashboard |
| `src/api/` | Thin read-only JSON API (standard library only) |
| `frontend/` | React app, with its own [README](frontend/README.md) |
| `config/` | All rules, weights, scenarios and the portfolio recipe (no magic numbers in code) |
| `data/` | Committed inputs and outputs; provenance in [data/SOURCES.md](data/SOURCES.md) |
| `tests/` | Unit, golden-scenario, end-to-end, API and app smoke tests |

## 3. Dataset Used

Full provenance and licences: [data/SOURCES.md](data/SOURCES.md). Nothing is downloaded at runtime.

| Dataset | What | Licence |
|---|---|---|
| GDELT GKG 2.1 | 27,784 news headlines, 10 Feb – 24 Mar 2022 (hourly sample, finance, economy, sanctions, energy and conflict themes, allow-listed outlets). Titles and links only | GDELT terms: free use with citation. **Citation:** The GDELT Project, https://www.gdeltproject.org/ |
| Kaggle stock tweets | 8,916 tweets about 25 tickers in the same window, **replayed historical data, not live X/Twitter**, sanitised (links removed, handles replaced) | CC0 (as declared by the uploader) |
| Daily returns | Derived returns only (Yahoo Finance via yfinance), used for evaluation and calibration | Raw prices are not redistributed |
| GDELT GKG 2.1, window N1 | 14,981 headlines, 6 Aug – 4 Sep 2026, same filters as W1, used as an out-of-sample calm-market test (news only) | Same GDELT terms |
| Synthetic portfolio | 44 positions worth $3,856.1m: 12 loans, 12 bonds, 6 swaps, 10 equities, 4 options. **Credit obligors are synthetic**; only equities and options use real tickers | Ours (MIT) |

The two text sources become **34,307 signals** and **3,678 event clusters**. The window is the run-up to and start of the Russia–Ukraine war. A small hand-written stub dataset is also included for tests.

**Limitations of the data.** News drives almost all stress triggers; the tweets cover no banks or energy names. GDELT timestamps are crawl times, not publisher times. Only English titles are used. Ratings, probabilities of default and sensitivities in the portfolio are illustrative.

## 4. Quickstart & Installation
Runtime: Python 3.13 on Windows 11 (CPU only, no network, no API keys)

```bash
git clone https://github.com/aishwaryspanwar/iiit-delhi-aishwary-panwar-hackathon.git
cd iiit-delhi-aishwary-panwar-hackathon
pip install -r requirements.txt
streamlit run src/app/dashboard.py
```

The dashboard has three tabs: **Signal feed** (a replay slider, impact timeline and filtered table), **Stress test** (KPIs, explanation, P&L by asset class and factor, positions and shocks) and **Try a headline** (live scoring with a what-if stress preview).

### Frontends

There are two frontends over the same Python engine and the same precomputed data. Streamlit is the reference UI. React (`frontend/`) is a parallel, more polished UI.

| | Command (repository root unless noted) | URL |
|---|---|---|
| Streamlit (reference) | `streamlit run src/app/dashboard.py` | http://127.0.0.1:8501 |
| API for React | `python -m src.api` | http://127.0.0.1:8000/api/health |
| React dev server | `cd frontend && npm install && npm run dev` | http://127.0.0.1:5173 |

React needs Node.js 20.19+ and the API running. To serve React from the API alone, run `npm run build` in `frontend/` once, then `python -m src.api` and open http://127.0.0.1:8000. Details, the API surface and screens: [frontend/README.md](frontend/README.md).

### Rebuild the data and run the tests

```bash
python -m src.pipeline --dataset w1      # rebuild signals, events and stress results (also: --dataset n1)
python -m scripts.evaluate               # recompute data/eval/metrics.json
python -m pytest -q                      # 179 tests
cd frontend && npm test                  # 10 frontend tests
```

Rebuilding is deterministic: an unchanged config reproduces the committed files, and a test fails if they drift.

## 5. Key Results & Domain Impact

**Signals.** The engine produces one structured signal per item with sentiment, event class, impact and its explanation, and groups 34,307 signals into 3,678 event clusters. Only 17 clusters (0.5%) exceed the trigger threshold of 7.

**Stress tests on the real window.** Eight clusters triggered a stress test. Each one lines up with a real event in the data:

| Date | Class | Impact | Event in the data | Portfolio P&L |
|---|---|---|---|---|
| 14 Feb | Geopolitical | 7.2 | Coverage of an "imminent invasion" peaks | −$71.5m (−1.85%) |
| 17 Feb | Geopolitical | 7.2 | US accuses Russia of a "false flag" pretext | −$71.5m (−1.85%) |
| 22 Feb | Geopolitical | 7.9 | Separatist regions recognised, sanctions announced | −$85.6m (−2.22%) |
| **24 Feb** | **Geopolitical** | **9.0** | **Full-scale invasion** | **−$115.2m (−2.99%)** |
| 28 Feb | Geopolitical | 7.4 | Emergency UN session, rouble crash | −$75.6m (−1.96%) |
| 7 Mar | Commodity/Energy | 7.3 | Oil surges toward $130 on a possible Russian import ban | −$36.1m (−0.94%) |
| 9 Mar | Credit event | 7.4 | Fitch cuts Russia deeper into junk | −$51.1m (−1.33%) |
| 16 Mar | Macroeconomic | 8.1 | Fed rate-hike coverage | −$53.8m (−1.40%) |

The invasion day scores highest and loses most. Routine war coverage on other days does not trigger, because the cluster score rewards abnormal attention, not just alarming wording (see [docs/impact_calibration.md](docs/impact_calibration.md)).

**Why it matters.** A risk team sees how a headline becomes a number. Every stress result carries the rules that matched, the trigger checks against their thresholds, the base and severity-scaled shocks, and a P&L attribution that sums exactly to the total.

**Evaluation.** Full details: [docs/evaluation.md](docs/evaluation.md). The reference labels come from an automated LLM annotation pass, applied blind to the text with a fixed [labelling guide](docs/labelling_guide.md) and not checked by a human. Headline numbers use the 100 representative items of a 150-item sample:

| Task | Accuracy | Macro-F1 | Majority baseline (acc. / macro-F1) |
|---|---|---|---|
| Event class, rule engine | **0.70** | **0.535** | 0.55 / 0.101 |
| Sentiment, VADER + finance lexicon | 0.42 | 0.417 | 0.70 / 0.275 |
| Sentiment, FinBERT (comparison) | 0.49 | 0.487 | 0.70 / 0.275 |

- **Event classification** clearly beats the baseline; most of its errors are items left as "other".
- **Sentiment is the weak component.** It catches most negative news but often calls neutral headlines positive, so it trails the always-neutral baseline on accuracy.
- **Repeat labelling:** a second, separate annotation session matched the first on all 30 items. That shows the annotator is consistent, not that its labels are correct.
- **Market check:** on the 8 trigger days the S&P 500 moved 1.63% on average (absolute), against 1.32% across the window.
- **No retuning:** the engine was not retuned on these labels.

**Out-of-sample test on a calm market (N1, Aug–Sep 2026).** The engine was run **unchanged** on a recent window it had never seen, chosen as the calmest recent stretch by VIX (news only, since the tweet data ends in 2022). Details in [docs/evaluation.md](docs/evaluation.md#6-out-of-sample-test-on-a-calm-window-n1).

| | W1 (war shock) | N1 (calm) |
|---|---|---|
| S&P 500 realised volatility | 24.4% | 8.2% |
| Highest cluster impact | 9.0 | 7.1 |
| Clusters above threshold | 17 | 2 |
| Stress tests fired | 8 | 1 |

- **The engine stays mostly quiet when markets are calm.**
- **The single N1 trigger** was a real escalation in the US–Iran conflict reported in the news. The S&P 500 rose that day, so against the market it was a false positive: the engine measures news severity, not market reaction.

**Limitations.**
- The impact score is a transparent rubric, not a trained predictor.
- The portfolio is synthetic and the stress is a sensitivity model, not a regulatory stress test or investment advice.
- The one-year expected-loss view understates loan losses from rating migration, so a lifetime view is shown beside it.
- The window is a single historical episode, replayed rather than live.
