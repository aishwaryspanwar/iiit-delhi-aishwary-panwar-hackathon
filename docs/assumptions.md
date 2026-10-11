# Assumptions and Simplifications

This page lists every modelling choice that is a judgement rather than a measurement, so a reader can challenge each one. Numbers live in `config/`; this page explains why they are what they are.

## 1. Data and sampling

- **GDELT sampling.** Every window uses the `:00` GKG file of each hour, one file in four. The engine converts mention counts to estimated full-feed counts (`config/ingestion.yaml`, `sampling_rate`) before applying volume thresholds, so the same thresholds apply to the live 15-minute feed (`gdelt_live`, rate 1.0).
- **Timestamps** are GDELT crawl times, usually within an hour of publication.
- **Tweets** are a replayed Kaggle dataset that ends on 30 Sep 2022, so N1 is news only. The tweets cover 25 tickers and no banks or energy names.
- **Only English titles** are scored; article bodies are never stored.

## 2. Evaluation protocol

- **W1 (Feb-Mar 2022) is the development window.** Rules, lexicon, sentiment bands, impact weights, trigger thresholds and the portfolio were set while looking at W1 and the W1 development sample.
- **W3 (Sep 2022) and N1 (Aug-Sep 2026) are untouched tests.** The configuration was frozen (git tag `eval-freeze`) before either window was scored, and the frozen config hash is stored in `data/eval/metrics.json`.
- **Labels.** Development and test labels come from an automated annotation pass that follows [labelling_guide.md](labelling_guide.md). The W3 test labels were made from the guide and the sheet only, without any model output or code.

## 3. Impact score

- The impact score is a transparent rubric, not a trained predictor. Weights are judgement, documented in `docs/impact_calibration.md`.
- The stream evaluates impact every hour on a rolling 24-hour window, using only data up to that hour. The volume baseline is the median of the same window at the same hour on the previous seven days, with quiet days counted as zero and a floor of 8 estimated mentions.
- A trigger needs at least 20 estimated mentions and 2 distinct outlets, so a handful of sampled headlines cannot fire a stress test through the baseline floor.

## 4. Stress scenarios

- **Market-wide shocks are calibrated, not chosen.** `scripts/calibrate_shocks.py` takes the worst 5-day window of historical analogue episodes that do not overlap any evaluation window (Crimea 2014, North Korea 2017, Soleimani 2020; taper tantrum 2013, Q4 2018; Aug 2011 downgrade, 2015-16 energy credit stress; Libya 2011, Abqaiq 2019). The base shock (impact 10) is twice the analogue mean; at the trigger threshold (impact 7) the shock equals the analogue mean. A test ties `config/shocks.yaml` to `data/market/shock_calibration.json`.
- **Spread proxies.** IG spread change = -(LQD - IEF return) / 8.5; HY = -(HYG - IEF return) / 4.0. These are approximate ETF spread durations.
- **In-scope add-ons are judgement:** extra spread widening, rating notches and equity excess for positions in the targeted country, sector or name.
- **Contagion** (`config/contagion.yaml`) gives linked countries a partial in-scope weight, for example Russia to Ukraine and Belarus (1.0), Kazakhstan (0.5), Poland, Hungary and Turkey (0.3). Judgement, based on trade, energy and proximity links.
- **Safe havens.** AAA to AA- sovereigns get no spread widening in any scenario.
- Historical geopolitical analogues moved broad markets little. The calibrated geopolitical scenario therefore produces most of its loss through targeted exposures, not through a market-wide sell-off.

## 5. Valuation

- **Bonds:** rate and spread duration plus convexity. Full cash-flow repricing agrees within 0.02% of value up to 100 bp and within 2% relative up to 250 bp (`tests/unit/test_model_correctness.py`).
- **Options:** delta, gamma and vega on a normalised spot of 100, checked against full Black-Scholes repricing.
- **Loans (banking book):** IFRS 9 expected credit loss. Every loan starts in stage 1. A loan moves to stage 2 (lifetime ECL) after a fall of three notches or more, or a move from investment grade to high yield, and to stage 3 at CCC. Lifetime PD = 1 - (1 - PD_1y)^maturity. The fair-value change of loans is shown for comparison but not booked.
- **Capital:** Basel III standardised risk weights by rating (corporates 20/50/75/100/150%, sovereigns 0/20/50/100/150%); extra capital is 8% of the RWA change. Operational and market-risk capital are out of scope.
- **Not modelled:** FX, correlation between factors, liquidity, counterparty credit risk on derivatives, and funding.

## 6. Portfolio

- The book represents a European wholesale bank with CEE and emerging-market corporate lending: 12 loans, 12 bonds, 6 interest-rate swaps, 10 listed equities and 4 equity options.
- **The CEE/EM tilt is deliberate** so that regional shocks are visible. It was chosen with knowledge of the 2022 shock, which is why the same book is run unchanged on W3 and N1.
- Credit obligors are synthetic (`Obligor-ENR-RU-01`); only equities and options use real tickers. Notionals are drawn from ranges with a fixed seed (42).
- **Equity betas are estimated** by OLS on 2021 daily returns against the S&P 500, before every evaluation window.
- Ratings, PDs and spreads are illustrative, monotone in rating and broadly in line with public long-run default studies.
