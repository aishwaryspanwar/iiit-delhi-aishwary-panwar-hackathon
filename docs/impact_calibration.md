# Impact Score — Design and Calibration

The impact score is a **documented, rule-based severity estimate**, not a trained predictor. The brief calls it a "predicted severity score"; we deliberately chose an explainable rubric whose every component is stored with the signal, and we sanity-check it against realised market moves in `docs/evaluation.md`. All weights live in `config/impact.yaml` (version `impact-v2`).

## 1. Item impact (one headline or tweet)

`item = clip(1 + 9 × (0.35·class_prior + 0.25·|sentiment| + 0.20·entity_importance + 0.20·cue_bonus), 1, 10)`

| Component | Range | Meaning |
|---|---|---|
| `class_prior` | 0.1–0.9 | Prior severity of the event class (geopolitical/credit 0.9, macro/commodity 0.7, regulatory 0.5 … other 0.1) |
| `sentiment_mag` | 0–1 | Absolute sentiment — strong language in either direction |
| `entity_importance` | 0.2–1.0 | Most important entity mentioned (US/Fed 1.0, Russia/China 0.9, mega-caps 0.6–0.8; 0.2 if none) |
| `cue_bonus` | 0–1 | Severity cues ("invasion", "default", "junk", "record", "biggest since"…), saturating at 2 hits |

## 2. Event (cluster) impact — what Module B consumes

Items are clustered by (day, event class, scope, primary target). A cluster's impact is:

`impact = clip(1 + 9 × (0.5·severity + 0.2·breadth + 0.3·abnormal_volume), 1, 10)`

| Component | Definition |
|---|---|
| `severity` | mean of the top-3 item impacts, rescaled to 0–1 |
| `breadth` | `log(distinct news outlets) / log(25)`, capped at 1 — tweets add no breadth |
| `abnormal_volume` | `log2(mentions / baseline) / 3`, clipped to 0–1, where `baseline` = median daily mentions of the **same** (class, scope, target) over the **previous 7 days** (floor 2). Uses only past data — no look-ahead. |

A cluster in the first 3 days of a dataset is flagged `warmup` (no baseline yet) and cannot trigger a stress test.

### Why v2 replaced v1
v1 used `mean(top-3 items) + 0.5·ln(outlets)`. On W1 it saturated: the Russia/Ukraine cluster scored 9–10 on almost every day from 11 Feb to 24 Mar, because in any busy cluster there are always three alarming headlines. That made 24 Feb (the invasion) indistinguishable from routine war coverage and produced 38–65 stress runs in six weeks.

What actually separates days is **abnormal attention**. On W1 (Russia country cluster):

| Day | Mentions | 7-day baseline | Severity | Breadth | Abnormal volume | v1 impact | **v2 impact** |
|---|---|---|---|---|---|---|---|
| 12 Feb (warnings) | 17 | 9.5 | 0.84 | 0.72 | 0.28 | 9.7 | **6.8** |
| 22 Feb (separatist regions recognised) | 70 | 19 | 0.81 | 0.86 | 0.63 | 9.7 | **7.9** |
| 24 Feb (invasion) | 162 | 28 | 0.90 | 0.96 | 0.84 | 10.0 | **9.0** |
| 28 Feb (SWIFT, rouble crash) | 107 | 61 | 0.86 | 0.97 | 0.27 | 10.0 | **7.4** |
| 15 Mar (ongoing war) | 56 | 54 | 0.83 | 0.80 | 0.02 | 9.7 | **6.2** |

## 3. Resulting distribution on W1 (3,678 clusters, 34,307 signals)
- Cluster impact percentiles: p50 2.9 · p90 4.5 · p95 5.1 · p99 6.6; **17 clusters (0.5%) above 7**.
- Item impact percentiles: p50 2.9 · p90 5.7 · p99 7.7.

## 4. Resulting stress triggers on W1
The "real-world event" column paraphrases each cluster's top-ranked headlines in the data.

Trigger = stress class ∧ impact > 7 ∧ confidence ≥ 0.6 ∧ sentiment ≤ 0.1 ∧ ≥ 2 news outlets ∧ not warm-up, with a 72-hour per-class cooldown that re-arms if impact rises by ≥ 1.

| Date | Class | Impact | Real-world event |
|---|---|---|---|
| 14 Feb | Geopolitical | 7.2 | Coverage of an "imminent invasion" peaks; markets weigh invasion vs Fed risk |
| 17 Feb | Geopolitical | 7.2 | Biden accuses Russia of a "false flag operation" to justify invasion |
| 22 Feb | Geopolitical | 7.9 | US calls Russia's moves an invasion; sanctions announced |
| **24 Feb** | **Geopolitical** | **9.0** | **"Full-scale invasion", attacks from many directions** (re-armed through cooldown: 9.0 ≥ 7.9 + 1) |
| 28 Feb | Geopolitical | 7.4 | UN emergency session; nuclear deterrence order; rouble crashes |
| 7 Mar | Commodity/Energy | 7.3 | Oil surges ~10% to $130 on a possible ban of Russian imports; Brent at 14-year high |
| 9 Mar | Credit Event | 7.4 | Fitch cuts Russia further into junk, says default is "imminent" |
| 16 Mar | Macroeconomic | 8.1 | Fed hike day; coverage dominated by rate-hike and recession risk |

Blocked: 4 warm-up clusters (10–12 Feb), 4 by cooldown, 1 by low confidence.

## 5. Honest caveats
- **In-sample calibration.** Component weights and thresholds were set by inspecting W1 itself; there is no out-of-sample window. The rubric is simple (4 + 3 interpretable components) to limit overfitting, and every number is visible to the user.
- **Known miss:** the 3 Mar Moody's/Fitch junk downgrades form a sparse two-headline credit cluster in the hourly GDELT sample (impact ≈ 4.4, watch-list level). We chose not to tune for it; the system escalates on 9 Mar when Fitch's further cut with "default imminent" arrives.
- Hourly GDELT sampling (1 in 4 files) scales mentions down roughly uniformly, so the ratio-based abnormal-volume term is largely unaffected, but small clusters are noisier.
- Impact is a severity ranking for triggering scenario analysis, **not** a forecast of returns. On 24 Feb the S&P 500 actually closed +1.5% after an intraday reversal — see the realised-move sanity check in `docs/evaluation.md`.
