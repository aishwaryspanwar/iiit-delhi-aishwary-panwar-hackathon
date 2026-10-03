# Data Availability Spike — Results

Run on: Windows 11, Python 3.13.5, local network, 2026-10-04.
Scripts: `scripts/spike/spike_gdelt.py`, `scripts/spike/spike_prices.py`, `scripts/spike/spike_finbert.py`.
Raw outputs (gitignored): `data/raw/spike_*.json`.

Candidate windows: **W1** 2022-02-10 → 2022-03-24 · **W2** 2022-04-25 → 2022-05-25 · **W3** 2022-09-10 → 2022-09-30.
Sampling: 10 random GKG 2.1 15-minute files per window (seed 20221).

## Gate results

| Gate | Check | W1 | W2 | W3 | Result |
|---|---|---|---|---|---|
| S1 | GKG files available (sampled) | 10/10 | 10/10 | 10/10 | PASS |
| S1 | Mean zipped file size | 4.48 MB | 5.16 MB | 4.65 MB | recorded |
| S2 | Records with non-empty `PAGE_TITLE` (gate ≥ 60%) | 99.9% | 99.6% | 99.8% | PASS |
| S3 | Finance-themed + allow-listed outlet unique titles per 15-min slot | 25.9 | 28.8 | 25.0 | — |
| S3 | Upper-bound titles/day (gate ≥ 150) | ~2,486 | ~2,765 | ~2,400 | PASS |
| S4 | Full-window download (gate ≤ 30 GB, ≤ 6 h) | 18.5 GB / 3.8 h | 15.4 GB / 3.2 h | 9.4 GB / 2.0 h | PASS |
| S5 | Kaggle `equinxx/stock-tweets-for-sentiment-analysis-and-prediction` | coverage 2021-09-30 → 2022-09-30, **CC0: Public Domain**, 18.7 MB | | | PASS (metadata) |
| S6 | Tweets in window (gate ≥ 2,000 total and ≥ 5 tickers with ≥ 50) | 8,916 rows / 7,313 unique texts; 13 tickers ≥ 50 | 8,972; 14 tickers | 3,113; 10 tickers | PASS |
| S7 | Daily prices: 25 tweet tickers + ^GSPC, ^VIX, ^TNX, XLE, XLF, XLK, XLI, XLU, XLY, XLP, XLB, HYG, LQD, IEF | 30 trading days, complete | 23, complete | 15, complete | PASS |
| S8 | Licences | see below | | | PASS |
| S9 | FinBERT CPU throughput (gate ≥ 20 items/s) | 25.8 items/s (batch 32, max_len 64, torch 2.14.1 CPU) | | | PASS |
| S10 | Stress-relevant headlines in the sample (geopolitical / monetary / credit / commodity) | 25 / 8 / 1 / 6 of 260 | 9 / 7 / 2 / 3 of 190 | 4 / 9 / 4 / 2 of 223 | W1 strongest |

Notes:
- S6: `stock_tweets.csv` (80,793 rows, 25 tickers, 2021-09-30 → 2022-09-29) was downloaded manually. In W1, TSLA (3,597) and TSM (2,046) dominate, while BX, ENPH, F, NOC and VZ have fewer than 10 tweets each. **Data-quality caveat:** the MSFT, PG and AMZN rows contain the same 402 tweets (1,206 rows, 402 unique texts). The uploader's `Stock Name` label is therefore unreliable, so entities come from text and cashtags, never from that column, and exact-text dedup removes 1,603 duplicates in W1. Some rows show mis-encoded characters (`�`), which normalization will clean.
- S7: one transient `database is locked` failure for KO came from yfinance's threaded cache. A single-threaded retry succeeded, so fetch scripts use `threads=False`.
- S3: the theme filter alone is loose (~718 finance-themed titles per slot, many off-topic). The outlet allow-list is the effective relevance filter, and the event rules filter further downstream.
- GPU: a GTX 1650 is present, but CPU throughput already passes, so the build does not depend on CUDA.

## Licences (S8)
| Source | Basis | What we commit |
|---|---|---|
| GDELT GKG 2.1 | gdeltproject.org Terms of Use: "unlimited and unrestricted use for any academic, commercial, or governmental use"; redistribution allowed with citation + link | Filtered headline, outlet, URL, derived fields, with GDELT citation |
| Kaggle stock tweets (equinxx) | CC0: Public Domain (as declared by uploader) | Sanitized tweet text for the window subset (handles/URLs removed) |
| Yahoo Finance via yfinance | Yahoo terms restrict redistribution of raw data | Derived daily returns only, plus the fetch script |
| ProsusAI/finbert | HF card has no licence field; source repo github.com/ProsusAI/finBERT is Apache-2.0 | Nothing (model downloaded at build time, pinned revision `4556d13015211d73dccd3fdd39d39232506f3e43`) |
| vaderSentiment 3.3.2 | MIT | Nothing (pip dependency) |

Model-loading note: the FinBERT repo has no `safetensors` weights on `main` (only unmerged bot PRs). We load `pytorch_model.bin` at a pinned revision. Transformers 5.x on torch 2.14 uses `weights_only` loading, and `trust_remote_code` is off. Build-time only; the runtime never loads it.

## Decision
- **Window: W1 (2022-02-10 → 2022-03-24).** All gates now pass, including S6. W1 is eligible on every measured gate and has the most distinct stress-relevant themes: the Russia–Ukraine invasion and sanctions, the commodity/energy shock, and the Fed's first hike on 2022-03-16.
- **GDELT acquisition: bulk GKG, hourly sample** (the :00 slot of each hour → 1,032 files, ~4.6 GB transient, ~1 h). Stream-and-filter, discarding raw zips. Expected ~600 allow-listed titles/day before cross-slot dedup, which is enough for clustering and breadth. The full 15-minute stream (18.5 GB / 3.8 h) also passes the gate and remains an option via a flag. **BigQuery is not needed.**
- **Sentiment: FinBERT as the build default**, with VADER as the runtime fallback and baseline.
