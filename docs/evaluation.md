# Evaluation

All numbers come from scripts and are pinned by tests:

- `python -m scripts.evaluate`: writes `data/eval/metrics.json` and `data/eval/window_comparison.json`.
- `python -m scripts.backtest_stress`: writes `data/eval/backtest.json`.
- `python -m scripts.benchmark`: writes `data/eval/benchmark.json`.
- `python -m scripts.render_results`: renders every table into [results.md](results.md).

`tests/unit/test_evaluate.py` fails if any committed file drifts from the code and data, or if the configuration hash differs from the one recorded in the metrics.

Sections 1 to 3 describe the frozen engine 0.2.0 (git tag `eval-freeze`), whose W3 and N1 results are the clean out-of-sample evidence. Section 4 describes the post-freeze engines 0.3.0 and 0.3.1 (shipped), and how their numbers differ. [results.md](results.md) shows the current (0.3.1) tables. Times are India Standard Time (IST).

## 1. Protocol

| Window | Role | Sources |
|---|---|---|
| W1, 10 Feb - 24 Mar 2022 (Russia-Ukraine war) | **Development and calibration.** Rules, sentiment bands, impact weights, trigger thresholds and the portfolio were set here. | GDELT + tweets |
| W3, 10 - 30 Sep 2022 (US CPI shock, Fed 75 bp, UK gilt crisis) | **Untouched test, shock window** | GDELT + tweets |
| N1, 6 Aug - 4 Sep 2026 (calmest recent stretch by VIX) | **Untouched test, calm window** | GDELT only |

- **The freeze.** The configuration was committed and tagged `eval-freeze` (config hash `4536f7568ed1`) before W3 and N1 were scored for the first time. No rule, weight or threshold of the 0.2.0 engine was changed afterwards.
- **Checking the freeze.** `python -m scripts.verify_freeze` checks the tag out into a temporary git worktree, classifies the test labels with the rules exactly as they stood there, and prints the macro-F1. It reproduces the 0.2.0 numbers below (W1 test 0.57, W3 test 0.40) and lists the config files that changed since the tag; `git diff eval-freeze -- config/` shows every post-freeze change line by line.
- **Label sets.**
  - W1 development: 200 items, used for tuning, with LLM annotation only.
  - W1 test: 150 items (100 representative plus 50 oversampled rare classes). Headline numbers use the 100 representative items.
  - W3 test: 120 representative items, drawn from cleaned raw documents before any W3 model output existed.
- **How the test labels were made.**
  - An automated LLM annotation pass, following [labelling_guide.md](labelling_guide.md).
  - The W3 pass ran in an isolated session that read only the guide and the sheet.
  - A human check is prepared in two stages, and `scripts.evaluate` uses a human label wherever one exists:
    - **Stage A:** 50 items labelled blind, to measure how often the LLM annotator agrees with a person.
    - **Stage B:** the rest confirmed or corrected.
  - The tables show how many items were human-verified at the time of the last run. At the time of writing that number is zero: every test score is against the LLM labels.
- **Text-based scoring.** The evaluation re-scores each labelled text through the current engine, so it never depends on pipeline internals such as de-duplication.

## 2. Pre-registered claims and what happened

Before scoring the test sets we wrote these claims down as tests.

| Claim | W1 test | W3 test |
|---|---|---|
| Event-class macro-F1 beats the majority baseline | Holds (0.57 vs 0.10) | Holds (0.40 vs 0.07) |
| Event-class macro-F1 beats a naive keyword classifier | **Did not hold** (0.57 vs 0.58) | Holds, within noise (0.40 vs 0.36) |
| FinBERT beats VADER on sentiment macro-F1 | Holds (0.57 vs 0.46) | **Did not hold** (0.44 vs 0.46) |

The claims that failed were removed from the test suite rather than tuned for, and they are reported here. The claims the README makes, and the tests that pin them, are:

- class and sentiment macro-F1 beat the majority baseline, with the lower end of the 95% interval above it;
- engine alerts are more precise than the base rate of stress days in both shock windows.

## 3. What the results say

Every number below is in [results.md](results.md).

- **Event classification transfers only partly.**
  - Macro-F1 falls from 0.84 on the development sample to 0.57 on W1 test and 0.40 on W3 test. The gap to development is the cost of tuning rules by hand on 200 items.
  - On W3 the main error is still items the rules leave as "other". The rules were written for a war window, and a monetary-policy window uses different vocabulary.
  - A keyword classifier is a hard baseline on headlines, and the rule engine does not beat it reliably.
- **Sentiment.**
  - FinBERT clearly beats VADER on W1 test, but not on W3, where both score about 0.45 macro-F1.
  - Accuracy is close to the always-neutral baseline, because most headlines are neutral.
  - Sentiment is only one of eight trigger checks; it caps how positive a cluster can be.
- **Impact against the market.**
  - Within one window the correlation of the daily maximum impact with the absolute S&P 500 move is weak and its interval includes zero (W1 +0.28, W3 +0.23, N1 -0.02).
  - Pooled over all three windows it is +0.41 [0.20, 0.60]. Most of that comes from shock windows scoring higher than the calm one, not from day-to-day ranking.
  - Impact does not track VIX changes or rate moves.
- **Triggers.**
  - In both shock windows, engine alerts are more precise than firing every day: W1 82% against a 67% base, and W3 80% against 67%, with recall 58% and 83%.
  - In W3 the alerts caught the US CPI shock (detected 10:30 IST on 13 Sep, before the CPI release at 18:00 IST and the S&P 500's −4.3% day), coverage ahead of the Fed decision on 21 Sep, and the gilt-market stress on 27 Sep, the day before the Bank of England's emergency gilt purchases (28 Sep).
  - **The calm window exposes false alarms.** N1 had no stress day at all, but the engine fired 4 alerts on US macro and Iran-Israel coverage. The engine measures how severe and abnormal the news is, not how markets will react.
- **Lead time.** Alerts fire a median of 9.5 hours (W1) and 12 hours (W3) before an end-of-day batch run would, and 83-100% of them before the US close.
- **Stress backtest.**
  - On the liquid sleeve (18 positions, equities and bond ETF proxies), the realised 1-day loss stayed within the stressed loss after 92% (W1), 88% (W3) and 75% (N1) of triggers.
  - Realised moves were negative after 50-62% of triggers over one day, against 57-73% of all days in the same windows.
  - Our scenarios are bounds, not forecasts: on the invasion day the market rallied.

## 4. Post-freeze vocabulary extension (engine 0.3.0)

**What changed.** To make the live "Try a headline" demo robust, 11 rules were added after the freeze (46 in total), together with severity cue words, 86 finance words in the VADER lexicon, and leader and capital aliases for India, the US, China and the UK. The new rules cover:

- policy actions: bans, tariffs, licence revocations, blocked deals, nationalisation, recalls, fines;
- relief actions: lifted bans, approvals, subsidies;
- corporate events: beats and misses, guidance changes, job cuts, fraud, production halts;
- coups and unrest, truces;
- supply shocks and credit stress: bail-outs, bank runs, missed payments;
- macro shocks and rate cuts.

Each rule carries a direction, so "India lifts ban on Chinese apps" reads as positive and "PM Modi bans Tesla in India" as a negative regulatory event targeting Tesla.

**Why it is reported separately.** The rules were written from general knowledge, without using any test label, but after W3 and N1 had been scored. For 0.3.0 those windows are therefore not untouched tests, and the frozen 0.2.0 numbers remain the clean estimate.

| Measure | 0.2.0 (frozen) | 0.3.0 (shipped) |
|---|---|---|
| Event class macro-F1, W1 test | 0.57 [0.43-0.69] | 0.59 [0.44-0.72] |
| Event class macro-F1, W3 test | 0.40 [0.28-0.54] | 0.35 [0.23-0.48] |
| VADER macro-F1, W1 / W3 test | 0.46 / 0.46 | 0.46 / 0.48 |
| W3 alerts: flags, precision, recall | 5, 80%, 83% | 6, 83%, 100% |
| W1 alerts: flags, precision, recall | 11, 82%, 58% | 12, 75%, 67% |
| N1 alerts (calm, all false alarms) | 4 | 8 |

**Reading it.**

- The wider vocabulary improves W1 test and alert recall in both shock windows.
- It lowers W3 event-class F1 and doubles the calm-window false alarms. One reason is that policy words pull items into the regulatory class that the annotator labelled otherwise; for example, an export ban on rice is labelled commodity.
- In W1, 0.3.0 alerts on 22 Feb at impact 8.2. The invasion-day cluster peaks at 8.9, below the re-arm margin of 9.2, so the 72-hour cooldown suppresses it and the next alert fires on 25 Feb.
- We did not tune further: adjusting rules after reading test errors would make the test sets meaningless.

## 5. Regression fix (engine 0.3.1)

A set of 35 well-known headlines from 2008-2024, all outside W1, W3 and N1 ([canary_headlines.csv](../data/eval/canary_headlines.csv)), exposed gaps that a jury would hit in the live demo: "Fitch downgrades Evergrande to restricted default" and "Silicon Valley Bank collapses after a run on deposits" were both read as Other, and "Taylor Swift" matched the SWIFT sanctions rule. Engine 0.3.1 adds one rule (CRD-008: bank failures, seizures, rescues and deposit runs, with exclusions such as West Bank and food banks), restricted and partial defaults, missed coupon, loan and IMF payments, and arrears.

- All 35 headlines are pinned by `tests/unit/test_rules.py`, together with a test that none of them falls inside an evaluation window.
- W1 development accuracy is unchanged (169 of 200), and so are every alert and every stress result in all three windows. W3 test macro-F1 is 0.35 either way.
- The set was used to write the rules, so it is a regression test, not an accuracy estimate.

## 6. Limitations

- **Labels:** until human verification completes, the test labels are a single LLM annotator. The blind Stage A sample measures how often it agrees with a person.
- **Sample size:** 100-120 test items per window give wide intervals, and several classes have fewer than ten examples.
- **Windows:** two shock windows and one calm window show behaviour, not stable error rates. The trigger statistics rest on 12-22 trading days per window.
- **Same-day matching:** the market check uses daily closes, so an alert after the close is matched to the next trading day.
