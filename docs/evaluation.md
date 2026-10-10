# Evaluation

All numbers come from `python -m scripts.evaluate`, which writes `data/eval/metrics.json`. A test (`tests/unit/test_evaluate.py`) fails if the committed metrics drift from the code and data.

## 1. Reference labels and how they were made

- **Sample:** 150 W1 items drawn by `scripts/make_label_sheet.py` (seed 20221).
  - **100 representative items:** stratified by source (70 news, 30 tweets) and ISO week.
  - **50 oversampled items:** chosen because the engine assigned one of six rare classes (credit event, regulatory, M&A, product launch, macroeconomic, commodity/energy).
- **Blind sheets:** the sheets contain only the date, source type and text, with no model output.
- **Who labelled:** an automated LLM annotation pass, following [labelling_guide.md](labelling_guide.md). **The labels were not checked by a human.** They are an independent second opinion, not human ground truth.
- **Repeat pass:** 30 of the items were labelled a second time in a separate chat session that could not see the first answers.

**Why the headline numbers use only the 100 representative items.** The 50 oversampled items were selected *because of* the engine's own prediction, which flatters it on those classes. They are used only for per-class detail (section 3).

## 2. Headline results (100 representative items)

| Task | Engine | Accuracy | Macro-F1 | Majority-class baseline (accuracy / macro-F1) |
|---|---|---|---|---|
| Event class (9 classes) | Rule engine | **0.70** | **0.535** | 0.55 / 0.101 ("other") |
| Sentiment (neg/neu/pos) | VADER + finance lexicon (build default) | 0.42 | 0.417 | 0.70 / 0.275 ("neu") |
| Sentiment (neg/neu/pos) | FinBERT (offline comparison) | 0.49 | 0.487 | 0.70 / 0.275 ("neu") |

**By source:**

| | Event-class accuracy / macro-F1 | VADER accuracy | FinBERT accuracy |
|---|---|---|---|
| News (70) | 0.64 / 0.534 | 0.49 | 0.47 |
| Tweets (30) | 0.83 / 0.455 | 0.27 | 0.53 |

**Reading the results.**
- **Event classification is the stronger component.** It beats the majority baseline by 15 points of accuracy and is five times better on macro-F1.
  - Its errors are almost all false negatives into "other": corporate news (10) and geopolitical items (7) that no rule matched.
  - When it does assign a specific class it is usually right. Geopolitical precision is 0.75 and M&A F1 is 0.91 on all 150 items.
- **Sentiment is the weak component.**
  - The annotator labelled 70% of items neutral, so always guessing "neutral" scores 70% accuracy. Both models score below that on accuracy, but above it on macro-F1, because they do detect polarity.
  - Negative news is mostly caught: VADER finds 13 of 18 negative items and FinBERT 14.
  - The dominant error is calling neutral headlines positive (VADER 32 times, FinBERT 28 times).
  - FinBERT is clearly better on tweets (0.53 against 0.27).
- **Why the stress triggers survive this.** The trigger uses sentiment only as a ceiling (cluster mean ≤ +0.10). The cluster score and the trigger checks average over many items and several outlets, which dampens item-level sentiment noise.

## 3. Per-class detail (all 150 items)

Precision and support on the oversampled classes are flattered by how they were sampled (see section 1).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Geopolitical | 0.75 | 0.41 | 0.53 | 22 |
| Macroeconomic | 0.60 | 0.67 | 0.63 | 9 |
| Credit event | 0.33 | 1.00 | 0.50 | 3 |
| Commodity/energy | 0.30 | 0.75 | 0.43 | 4 |
| Regulatory | 0.13 | 0.20 | 0.15 | 5 |
| Merger/acquisition | 0.91 | 0.91 | 0.91 | 11 |
| Earnings/corporate | 0.67 | 0.13 | 0.22 | 15 |
| Product launch | 0.36 | 0.67 | 0.47 | 6 |
| Other | 0.68 | 0.69 | 0.69 | 75 |

## 4. Repeat-labelling consistency (30 items)

The second session reproduced the first exactly: 100% agreement on class and sentiment (Cohen's κ = 1.0), including identical notes.

This shows the annotator is **run-to-run consistent** under the same instructions. It is **not** evidence that the labels are correct, and it is not a human inter-annotator agreement.

## 5. Impact sanity check against the market

The check compares the S&P 500 on the trading day of each of the 8 triggered stress tests with all 30 trading days in the W1 window (`data/market/returns_daily.csv`).

- Mean absolute S&P 500 move: **1.63%** on trigger days against **1.32%** on all days.
- 5 of the 8 trigger days closed down. The VIX rose on 5 of 8.
- The invasion day (24 Feb, impact 9.0) is the notable exception: the S&P 500 reversed intraday to close up 1.5%.

This is a coarse plausibility check over 8 days, not a test of predictive power: the impact score is a severity estimate of the news, not a return forecast.

## 6. Out-of-sample test on a calm window (N1)

**Question:** does the engine stay quiet when markets are calm? All rules, weights and thresholds were set on W1 (a war shock). N1 is a later window the engine had never seen, run with **no changes**.

**Window choice.** N1 runs from 6 Aug to 4 Sep 2026, chosen from market data as the calmest recent stretch: the VIX closed around 15 and never above 16.5. It is **news only**: the tweet dataset ends in September 2022, so there is no social source for 2026. It uses the same GDELT sampling, theme filter and outlet allow-list as W1. Numbers come from `data/eval/window_comparison.json`.

| | W1 (Feb–Mar 2022) | N1 (Aug–Sep 2026) |
|---|---|---|
| Signals / event clusters | 34,307 / 3,678 | 14,434 / 1,988 |
| Cluster impact, median / p90 / p99 | 2.9 / 4.5 / 6.6 | 2.8 / 4.4 / 6.1 |
| Highest cluster impact | 9.0 | 7.1 |
| Clusters above the trigger threshold (7) | 17 (0.5%) | **2 (0.1%)** |
| Stress tests fired | 8 | **1** |
| S&P 500 realised volatility (annualised) | 24.4% | 8.2% |
| S&P 500 worst day | −2.95% | −0.87% |

**Reading the results.**
- **The engine mostly stays quiet in calm markets.** Day-to-day cluster scores look almost identical in both windows; what differs is the tail. W1 has 17 clusters above 7, peaking at 9.0. N1 has two, peaking at 7.1, just over the line.
- **The one N1 stress test (3 Sep 2026, impact 7.1, −$56.5m, −1.46%)** was not noise in the text. The headlines in the cluster report a US strike in Iran, Iranian warnings of a large-scale attack, and an attack on Kuwait, all within an ongoing US–Israel conflict with Iran covered throughout the window.
- **Against the market, it was a false positive.** The S&P 500 rose 1.1% that day and the VIX fell. The engine scores the severity of the news, not whether markets will react to it. That is the main limitation this test exposes.
- **The second above-threshold cluster (6 Aug, 7.1) was correctly blocked.** It fell inside the 3-day warm-up, before a volume baseline existed.

## 7. Limitations

- **Reference labels:** they come from a single LLM annotator with no human check. Disagreement can reflect annotator error as well as engine error.
- **Sample size:** 100 representative items give wide confidence intervals. Each rare class has fewer than 10 examples.
- **Out-of-sample scope:** one shock window (W1) and one calm window (N1, news only) are not enough to estimate false-alarm rates; they show behaviour, not statistics.
- **No retuning:** the engine's rules and sentiment lexicon were **not** retuned on these labels, so the results are not contaminated by fitting to the test set. The clear next steps would be a wider neutral band for sentiment, FinBERT for tweets, and more corporate and geopolitical rule patterns, all validated on a fresh sample.
