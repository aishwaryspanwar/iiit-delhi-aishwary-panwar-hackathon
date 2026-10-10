# Impact Score: Design and Calibration

The impact score is a **documented, rule-based severity estimate**, not a trained predictor. Every component is stored with the signal or event, and all weights live in `config/impact.yaml` (`impact-v2`). All design choices on this page were made on **W1 (Feb-Mar 2022), the development window**. W3 and N1 were scored only after the configuration was frozen (git tag `eval-freeze`).

## 1. Item impact (one headline or tweet)

`item = clip(1 + 9 × (0.35·class_prior + 0.25·|sentiment| + 0.20·entity_importance + 0.20·cue_bonus), 1, 10)`

| Component | Range | Meaning |
|---|---|---|
| `class_prior` | 0.1-0.9 | Prior severity of the event class (geopolitical and credit 0.9, macro and commodity 0.7, regulatory 0.5, other 0.1) |
| `sentiment_mag` | 0-1 | Absolute FinBERT sentiment: strong language in either direction |
| `entity_importance` | 0.2-1.0 | Most important entity mentioned (US and the Fed 1.0, Russia and China 0.9, mega-caps 0.6-0.8; 0.2 if none) |
| `cue_bonus` | 0-1 | Severity cues ("invasion", "default", "junk", "record", "biggest since"), saturating at two hits |

## 2. Event impact, computed as of every hour

Signals are grouped by (event class, scope, primary target). Every hour the stream looks at the **rolling 24 hours up to that hour** and computes:

`impact = clip(1 + 9 × (0.5·severity + 0.2·breadth + 0.3·abnormal_volume), 1, 10)`

| Component | Definition |
|---|---|
| `severity` | mean of the top-3 item impacts in the window, rescaled to 0-1 |
| `breadth` | `log(distinct news outlets) / log(25)`, capped at 1 (tweets add no breadth) |
| `abnormal_volume` | `log2(mentions / baseline) / 3`, clipped to 0-1 |

- **Mentions** are estimated full-feed counts: each item's duplicate count divided by its source's sampling rate (GDELT hourly sample 0.25; tweets 1.0).
- **Baseline** is the median of the same 24-hour window at the same hour on each of the previous 7 days, with **quiet days counted as zero**, and a floor of 8 estimated mentions.
- **No look-ahead.** Nothing after the hour being evaluated is used; a test appends future items and checks that earlier alerts do not change.
- The first 3 days of a dataset are a **warm-up** without a baseline.

The daily event record shows the **peak** as-of impact during that day (`peak_at`) and, if an alert fired, its `detected_at` time.

### Why abnormal volume matters
In any busy story there are always three alarming headlines, so severity alone saturates. On W1 an early version scored the Russia cluster 9-10 almost every day and fired 38-65 stress tests in six weeks. What separates the invasion day from routine war coverage is **abnormal attention**: the volume term rises when coverage jumps relative to its own recent history.

## 3. Trigger checks (evaluated every hour)

An alert fires at the first hour in which all checks pass:

| Check | Threshold |
|---|---|
| Stress-relevant class | geopolitical, macroeconomic, credit event, commodity/energy, regulatory |
| Impact | > 7 (the brief's example threshold) |
| Classification confidence (window mean) | ≥ 0.6 |
| Sentiment (window mean) | ≤ +0.10 |
| Not a positive credit action | share of upgrades ≤ 50% |
| Corroboration | ≥ 2 distinct news outlets |
| Volume | ≥ 20 estimated mentions |
| Baseline | not in warm-up |
| Cooldown | 72 hours per (class, target group), re-armed if impact rises by ≥ 1. Countries fully linked in `config/contagion.yaml` (for example Ukraine and Belarus to Russia) share one cooldown |

## 4. Result on the development window (W1)

- 34,298 signals, 4,243 daily event records, 54 above impact 7.
- 12 alerts: five on the Russia-Ukraine escalation (14, 17, 22, 24 and 28 Feb), oil on 7 Mar, Fitch's Russia downgrade on 9 Mar, gas on 9 Mar, US CPI on 10 Mar, Fed coverage on 14 and 16 Mar, and China-Russia reports on 15 Mar.
- On 24 Feb, an earlier Ukraine-scoped cluster passed every check at 04:00 UTC, about an hour after the invasion began, but was suppressed by the cooldown from the 22 Feb alert. The re-armed alert fired at 12:00 UTC at impact 8.1.
- The market and trigger statistics for every window, with confidence intervals, are in `docs/evaluation.md`.

## 5. Honest caveats

- Weights and thresholds were chosen on W1 by inspection. W3 and N1 are the out-of-sample check.
- Impact measures the severity of the news, not the market's reaction. It is a ranking to decide when to run scenario analysis, not a return forecast.
- Hourly GDELT sampling keeps relative volumes but makes small clusters noisy; the volume and outlet checks exist to stop thin clusters from firing.
