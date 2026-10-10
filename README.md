# Event-Driven Risk Engine & Portfolio Stress Testing - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Aishwary S Panwar
**College Email ID:** aishwary23055@iiitd.ac.in
**College / Campus:** IIIT Delhi
**Demo Video Link:** _to be added_
**Slide Deck Link (if hosted externally):** not hosted externally; the deck will be committed as `docs/presentation.pdf`

## 1. Project Overview / Problem Statement & Approach

**Problem.** News and social posts move markets hours before a risk system sees a number. The brief asks for an NLP engine that turns unstructured text from at least two sources into structured signals (sentiment, event class, 1-10 impact), exposed through a file or API, and at least one downstream module.

**What this project does.**
1. **Risk engine.** Reads GDELT news headlines and stock tweets, de-duplicates them, tags 241 companies, countries, sectors and central banks, classifies each item into one of nine event classes, scores sentiment with FinBERT, and scores impact with a transparent rubric.
2. **As-of stream.** Every hour it recomputes each event's impact on a rolling 24-hour window using only data available at that hour, and fires an **alert** the first hour an event passes eight checks. This is how the system would run on a live feed (an optional live GDELT mode is included).
3. **Module B, event-triggered stress test.** Each alert stresses a synthetic wholesale-banking book with scenarios **calibrated on historical analogue episodes**. It reports value before and after, IFRS 9 provisions, risk-weighted assets, a severity curve and P&L attribution that sums exactly to the total.

**Approach.** Every number is traceable to a rule, a weight or a data file, and the model is validated the way a risk team would demand. Rules and thresholds were tuned on one window (W1), the configuration was frozen (git tag `eval-freeze`), and only then were two untouched windows scored: W3, a September 2022 rates shock, and N1, a calm 2026 month. Results are reported with confidence intervals, naive baselines and the claims that failed. No LLM is in the scoring path, and everything runs offline on a CPU.

## 2. Architecture & Tech Stack

![Architecture](docs/architecture.png)

| Stage | How it works |
|---|---|
| Clean and de-duplicate | Strip HTML, links and handles; hash de-duplication that ignores trailing outlet and section tags, keeping duplicate counts and outlets |
| Entities and scope | 241 entities and cashtags decide whether an event is single-name, sector, country or macro |
| Event class | 35 weighted rules over 9 classes, with exclusions (sport, crime, consumer debt) and credit **direction** (a rating upgrade is not a stress event) |
| Sentiment | FinBERT (`ProsusAI/finbert`, pinned revision, CPU), neutral band chosen on the development sample; VADER with a finance lexicon as the live fallback |
| Item impact | `1 + 9 × (0.35·class prior + 0.25·sentiment magnitude + 0.20·entity importance + 0.20·severity cues)`, components stored |
| As-of event impact | Every hour, on a rolling 24 h window per (class, scope, target): `1 + 9 × (0.5·severity + 0.2·breadth + 0.3·abnormal volume)`. The baseline is the same hour on the previous 7 days, quiet days counted as zero, with no look-ahead ([details](docs/impact_calibration.md)) |
| Alert | Stress class, impact > 7, confidence ≥ 0.6, sentiment ≤ +0.1, not an upgrade, ≥ 2 outlets, ≥ 20 estimated mentions, past warm-up, and a 72 h cooldown per target group |
| Stress scenarios | Market shocks = 2× the worst week of historical analogues (Crimea 2014, taper tantrum 2013, US downgrade 2011, Libya 2011 and others) scaled by impact; targeted add-ons and contagion to linked countries; AAA/AA sovereigns are safe havens |
| Valuation | Bonds: rate and spread duration plus convexity. Loans: IFRS 9 staging (stage 2 → lifetime ECL). Swaps: DV01. Equities: estimated beta. Options: delta, gamma, vega. Capital: Basel III standardised RWA |

- **Precompute plus a thin runtime.** `python -m src.pipeline` writes versioned, schema-validated files (signals, events, alerts, stress results). The frontends and the API only read them. Builds are deterministic and tests check that committed outputs are current.
- **Two frontends, one engine.** Streamlit is the reference UI and the Quickstart. React is the polished UI, served by a standard-library JSON API that calls the same Python code.
- **Stack.**
  - Runtime: Python 3.13, pandas, numpy, PyYAML, jsonschema, vaderSentiment, Streamlit, Plotly.
  - Frontend: React 19, TypeScript, Vite, Tailwind CSS, Recharts.
  - Build only: PyTorch and transformers (FinBERT), yfinance, matplotlib.

| Path | Contents |
|---|---|
| `src/riskengine/` | Cleaning, de-duplication, entities, rules, sentiment, impact, schemas |
| `src/stream/` | As-of streaming engine: rolling windows, baselines, alerts |
| `src/stress/` | Portfolio, calibrated shocks, contagion, valuation, IFRS 9, capital, explanations |
| `src/api/`, `frontend/`, `src/app/` | JSON API, React app, Streamlit app |
| `scripts/` | Data fetching, labelling, calibration, evaluation, backtest, benchmark, live mode, diagram |
| `config/` | Every rule, weight, threshold, scenario and the portfolio recipe (no magic numbers in code) |
| `data/` | All inputs and outputs, with provenance in [data/SOURCES.md](data/SOURCES.md) |
| `docs/` | [results](docs/results.md), [evaluation](docs/evaluation.md), [impact calibration](docs/impact_calibration.md), [assumptions](docs/assumptions.md), [labelling guide](docs/labelling_guide.md) |

## 3. Dataset Used

All data is public or synthetic; nothing is downloaded at runtime. Full provenance and licences: [data/SOURCES.md](data/SOURCES.md).

| Window | Role | News (GDELT GKG 2.1) | Tweets (Kaggle, CC0) |
|---|---|---|---|
| W1, 10 Feb - 24 Mar 2022 (Russia-Ukraine war) | Development and calibration | 27,784 headlines | 8,916 |
| W3, 10 - 30 Sep 2022 (US CPI, Fed 75 bp, UK gilt crisis) | Untouched test, shock | 12,773 | 3,113 |
| N1, 6 Aug - 4 Sep 2026 (calmest recent month) | Untouched test, calm | 14,981 | none (dataset ends 2022) |

Other data:

- **Derived market returns.** Only derived series from yfinance are committed: raw prices are never redistributed, and none of it is used in scoring.
- **Synthetic portfolio.** 44 positions worth $3,646.9m: loans, bonds, swaps, equities and options. Credit obligors are synthetic; equities and options use real tickers.
- **Evaluation labels.** 200 development items plus 270 test items. Labels come from an automated LLM annotation pass, and the test labels are checked by a person.

**Assumptions.**

- GDELT timestamps are crawl times.
- The hourly sample is one GKG file in four, and counts are scaled accordingly.
- Tweets are replayed, not live.
- The portfolio deliberately tilts to CEE and emerging markets so regional shocks show. Because that choice was made knowing W1, the same book runs unchanged on W3 and N1.

Every judgement is listed in [docs/assumptions.md](docs/assumptions.md).

## 4. Quickstart & Installation

Runtime: Python 3.13 on Windows 11 (also runs on macOS and Linux). CPU only, no network, no API keys. React needs Node.js 20.19 or later.

```bash
git clone https://github.com/aishwaryspanwar/iiit-delhi-aishwary-panwar-hackathon.git
cd iiit-delhi-aishwary-panwar-hackathon
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/app/dashboard.py
```

The Streamlit app opens at http://127.0.0.1:8501 with four tabs:

- **Signal feed:** replay, impact timeline and filters.
- **Stress test:** P&L, IFRS 9, capital and the severity curve.
- **Alerts and evaluation.**
- **Try a headline:** live scoring and a what-if preview.

**React app.**

```bash
python -m src.api                  # API on http://127.0.0.1:8000
cd frontend && npm install && npm run build   # once; then open http://127.0.0.1:8000
```

The React app has seven pages: Overview with real-time alerts, Signal feed, Companies, Stress test, Evaluation, Try a headline and Methodology. For development, use `npm run dev` (http://127.0.0.1:5173). Details are in [frontend/README.md](frontend/README.md).

**Rebuild, evaluate, test.**

```bash
pip install -r requirements-build.txt         # PyTorch, transformers, yfinance (build only)
python -m src.pipeline --dataset w1           # also w3, n1, stub
python -m scripts.evaluate                    # metrics.json, window_comparison.json
python -m scripts.backtest_stress             # backtest.json
python -m scripts.benchmark                   # benchmark.json
python -m scripts.render_results              # docs/results.md
python -m pytest -q                           # 264 tests
cd frontend && npm test                       # 14 tests
```

Optional live mode, which needs network: `python -m scripts.live_gdelt` polls GDELT every 15 minutes and writes signals, events and alerts to `data/processed/live/`.

## 5. Key Results & Domain Impact

Full tables, with 95% confidence intervals: [docs/results.md](docs/results.md). Method and limitations: [docs/evaluation.md](docs/evaluation.md).

**Alerts on the untouched shock window (W3, Sep 2022).**

- The engine fired 8 alerts on 5 trading days, with 80% precision and 83% recall against market-stress days (|S&P 500| > 1.5% or VIX +10%). Firing every day would score 67% precision.
- It flagged the US inflation story at 05:00 UTC on 13 Sep, hours before the CPI release and the S&P 500's −4.3% day.
- It also flagged the Fed's 75 bp decision (21 Sep) and the Bank of England's gilt intervention (27 Sep).
- Alerts arrive a median of 12 hours before an end-of-day batch run would see the same event, and all of them before the US close.

**Calm window (N1).** There were no market-stress days at all, yet the engine fired 4 alerts on US macro and Iran-Israel news. These are false alarms in market terms: the engine measures how severe and abnormal the news is, not how markets will react.

**Stress results.**

- The calibrated scenarios cost the book −0.2% to −2.3% per alert.
- Credit events are the most severe: Fitch's Russia downgrade cost −$83.0m, mostly IFRS 9 stage-2 provisions on Russian loans.
- Geopolitical market shocks are mild, because historical analogues show broad markets rarely fall far on geopolitics. The loss sits in the targeted exposures.
- In the backtest, the realised loss on the liquid sleeve stayed within the stressed loss after 88-92% of triggers in the shock windows (1-day horizon).

**NLP quality on held-out labels.**

| Model | W1 test | W3 test | Majority baseline | Keyword baseline |
|---|---|---|---|---|
| Event class, macro-F1 | **0.57** [0.43-0.69] | **0.40** [0.28-0.54] | 0.10 / 0.07 | 0.58 / 0.36 |
| Sentiment (FinBERT), macro-F1 | **0.57** [0.43-0.68] | **0.44** [0.34-0.54] | 0.27 / 0.25 | VADER 0.46 / 0.46 |

Both models clearly beat the majority baseline. Two claims we wrote down before scoring did not hold:

- the rules do not beat a naive keyword classifier on W1 test;
- FinBERT does not beat VADER on W3.

Both are reported rather than tuned away. Event-class accuracy also falls on the rates-shock window, where the vocabulary differs from the war window the rules were written on.

**Why it matters.** A risk team sees within hours which headline moved which number:

- the matched rules and the impact components;
- the checks against their thresholds;
- the calibrated shocks and the analogue episodes behind them;
- the IFRS 9 stage moves and the capital cost.

Each piece can be audited, challenged and re-run from configuration. The engine is a triage layer that decides when to run scenario analysis, not a market forecaster, and the evaluation shows where that line is.

**Throughput.** 2,463 items/s end to end with VADER on a laptop CPU. FinBERT scores 24 items/s, so a 15-minute GDELT file is scored well within its interval.

**Limitations.**

- Test labels are LLM annotations under human verification.
- 100-120 test items per window and 14-28 trading days give wide intervals.
- The impact score is a rubric, not a trained predictor.
- The portfolio and its ratings are synthetic.
- Valuation is first- and second-order sensitivity: no FX, correlation, liquidity or counterparty risk.
- This is not a regulatory stress test and not investment advice.
