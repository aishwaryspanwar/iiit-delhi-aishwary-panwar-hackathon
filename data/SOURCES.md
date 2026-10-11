# Data Sources, Provenance and Licences

Everything needed to run the prototype is in this folder; nothing is downloaded at runtime.
Raw downloads live in `data/raw/` (gitignored) and are reproducible with the fetch scripts below.
No real or confidential client data is used anywhere. The portfolio and every rating, PD and sensitivity in it is synthetic.

## Text sources

| File | What it is | Source | Licence / terms | How to regenerate |
|---|---|---|---|---|
| `sources/w1/gdelt_headlines.csv` | **27,784** news headlines, 2022-02-10 to 2022-03-24 (development window), from GDELT GKG 2.1, the `:00` file of every hour. Only allow-listed financial and general news outlets whose GKG themes are finance, economy, sanctions, energy or conflict related, with titles of at least 25 characters. Columns: GKG record id, crawl timestamp (UTC), outlet, URL, page title. | The GDELT Project, http://data.gdeltproject.org/gdeltv2/ | GDELT Terms of Use: unlimited, unrestricted use; redistribution allowed with citation and a link to https://www.gdeltproject.org/. **Citation:** The GDELT Project, https://www.gdeltproject.org/. Headlines remain the property of their publishers; only titles and links are stored, never article bodies. | `python -m scripts.fetch_gdelt` |
| `sources/w3/gdelt_headlines.csv` | **12,773** headlines, 2022-09-10 to 2022-09-30 (test window: US CPI shock, Fed 75 bp, UK gilt crisis), same sampling and filters as W1. | Same | Same | `python -m scripts.fetch_gdelt --window w3 --start 2022-09-10 --end 2022-09-30` |
| `sources/n1/gdelt_headlines.csv` | **14,981** headlines, 2026-08-06 to 2026-09-04 (test window, the calmest recent stretch by VIX), same sampling and filters. News only, because the tweet dataset ends in September 2022. | Same | Same | `python -m scripts.fetch_gdelt --window n1 --start 2026-08-06 --end 2026-09-04` |
| `sources/w1/tweets.csv`, `sources/w3/tweets.csv` | **8,916** (W1) and **3,113** (W3) tweets about 25 stock tickers, **replayed historical data**, not live X/Twitter. URLs removed, user handles replaced with `@user`. Columns: source row id, timestamp (UTC), text. The uploader's ticker column is dropped because it is unreliable. | Kaggle: `equinxx/stock-tweets-for-sentiment-analysis-and-prediction` (Hanna Yukhymenko), `stock_tweets.csv` | CC0: Public Domain (as declared by the uploader). Tweet authors retain rights in their own words; only the sanitised window subsets are stored. | Download `stock_tweets.csv` into `data/raw/`, then `python -m scripts.fetch_tweets` (W1) or `python -m scripts.fetch_tweets --window w3 --start 2022-09-10 --end 2022-09-30` |
| `eval/canary_headlines.csv` | 35 well-known headlines (2008-2024) from outside every evaluation window, with the expected class and direction. A regression set for the rules, written for this project; used during development, so it is not an accuracy estimate | n/a |
| `stub/stub_documents.csv` | 41 hand-written sample items used for the stub vertical slice and tests. Original wording. | Written for this project | Ours (MIT) | n/a |

## Market data (derived returns only)

Yahoo's terms restrict redistribution of raw prices, so only **derived** series are committed. None of these is used in scoring; they serve calibration and evaluation only.

| File | What it is | How to regenerate |
|---|---|---|
| `market/returns_daily.csv`, `returns_daily_w3.csv`, `returns_daily_n1.csv` | Daily simple returns around each window for the 25 tweet tickers, S&P 500, VIX (relative change), sector and bond ETFs; `^TNX_change_bp` is the daily change of the US 10-year yield in basis points | `python -m scripts.fetch_prices [--start ... --end ... --out ...]` (see `docs/evaluation.md`) |
| `market/returns_daily_2021.csv` | Daily returns for calendar 2021, used only to estimate equity betas before every evaluation window | `python -m scripts.fetch_prices --start 2020-12-30 --end 2022-01-01 --out data/market/returns_daily_2021.csv` |
| `market/returns_episodes.csv` | For each historical analogue episode (2011-2020): index and ETF levels relative to the episode start, 10-year yield change in bp and VIX change in points from the start | `python -m scripts.calibrate_shocks --download` |
| `market/shock_calibration.json` | Worst 5-day moves per episode and the resulting base shock per scenario (2x the analogue mean) | `python -m scripts.calibrate_shocks` |

## Portfolio and model outputs

| File | What it is | How to regenerate |
|---|---|---|
| `portfolio/portfolio_v2.csv` | Synthetic wholesale-banking book: 12 loans, 12 bonds (3 FRNs, 5 sovereigns), 6 interest-rate swaps, 10 equities, 4 listed equity options. Credit positions use synthetic obligor names (`Obligor-ENR-RU-01`); equities and options use real tickers with betas estimated on 2021 returns. Seed 42. Rationale in `docs/assumptions.md`. | `python -m src.stress.portfolio_gen` |
| `processed/<window>/signals_v1.jsonl.gz` | **The engine's output contract**: one structured signal per de-duplicated item (sentiment, event class and direction, impact with components, entities, scope) | `python -m src.pipeline --dataset <window>` |
| `processed/<window>/events_v1.jsonl.gz` | Daily event records per (class, scope, target) with peak as-of impact, rolling-window statistics and detection time | same |
| `processed/<window>/alerts_v1.jsonl.gz` | Alerts fired by the hourly stream: detection time, impact at detection, the checks that passed | same |
| `processed/<window>/stress_results_v1.json` | Module B: trigger decision for every event record and a full stress result for every alert | same |

## Evaluation files

| File | What it is | How to regenerate |
|---|---|---|
| `eval/labels_w1_dev_sheet.csv` (+ `_key.csv`) | 200 W1 development items, automated annotation, used for tuning | `python -m scripts.make_label_sheet --window w1 --split dev --size 200 --seed 20222 --prefix D --exclude data/eval/labels_key.csv` |
| `eval/labels_sheet.csv` (+ `labels_key.csv`) | 150 W1 test items (100 representative, 50 oversampled), automated annotation; `relabel_*` is a 30-item repeat pass | committed key is authoritative (drawn from an earlier build) |
| `eval/labels_w3_test_sheet.csv` (+ `_key.csv`) | 120 W3 test items drawn from cleaned raw documents before any W3 model output existed; annotated from the guide and the sheet only, without model output | `python -m scripts.make_label_sheet --window w3 --split test --size 120 --seed 20223 --prefix T` |
| `eval/finbert_eval_scores.json` | FinBERT scores for every labelled text, keyed by text hash, so the evaluation runs without PyTorch | written by `scripts.evaluate` when PyTorch is available |
| `eval/metrics.json`, `window_comparison.json`, `backtest.json`, `benchmark.json` | Evaluation results; rendered into `docs/results.md` | `python -m scripts.evaluate`, `scripts.backtest_stress`, `scripts.benchmark`, `scripts.render_results` |

## Models

| Model | Basis | What we commit |
|---|---|---|
| `ProsusAI/finbert` at revision `4556d13` | Apache-2.0 (source repository github.com/ProsusAI/finBERT) | Nothing; downloaded at build time, run on CPU. Scores are cached in `data/raw/` (gitignored) |
| vaderSentiment 3.3.2 | MIT | Nothing (pip dependency) |

## Assumptions about the data
- GDELT timestamps are **crawl times**, usually within an hour of publication.
- Hourly sampling (one GKG file in four) is a volume control. The engine scales mention counts by the sampling rate before applying volume thresholds.
- The tweets are dominated by a few tickers (TSLA, TSM) and cover no banks or energy names, so **news drives almost all alerts**.
- Only English titles are used.
