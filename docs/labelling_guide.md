# Labelling Guide (blind evaluation set)

**Files:** `data/eval/labels_sheet.csv` (150 items, do first) and later `data/eval/relabel_sheet.csv` (30 items, do **at least one day later**, without looking at your first answers).
**Time:** about 3–4 hours for 150 items. Open the CSV in Excel/Sheets, fill only the `event_class`, `sentiment` and (optional) `notes` columns, save as CSV (UTF-8) with the same name.
**Do not** open `labels_key.csv`, the processed signal files, or the dashboard while labelling — the point is that your labels are independent of the model.

## Column `event_class` — pick exactly one (use the code)

| Code | Use when the item is mainly about… | Examples |
|---|---|---|
| `geopolitical` | war, military action, sanctions, diplomacy, territorial disputes, international tensions | "Russia launches invasion", "EU agrees new sanctions" |
| `macroeconomic` | central banks, interest rates, inflation, GDP, jobs, yields, currencies, the economy as a whole | "Fed raises rates", "CPI hits 40-year high", "rouble plunges" |
| `credit_event` | defaults, bankruptcies, debt restructuring, **credit** rating actions, credit spreads | "Moody's cuts Russia to junk", "firm files for Chapter 11" |
| `commodity_energy` | oil, gas, power, metals, agricultural commodities, energy supply | "Brent tops $130", "wheat hits record" |
| `regulatory` | regulators, fines, lawsuits, investigations, new laws and rules affecting companies | "SEC probes trading", "antitrust suit filed" |
| `merger_acquisition` | takeovers, mergers, acquisitions, stake purchases, buyouts | "X agrees to buy Y" |
| `earnings_corporate` | results, guidance, analyst ratings on **stocks**, dividends, buybacks, management changes, IPOs, other company news | "Q4 profit beats", "analyst cuts Apple to hold" |
| `product_launch` | new products or services launched/unveiled | "Apple unveils new iPhone" |
| `other` | anything else, incl. sport, culture, opinion with no event, generic market chatter, spam | "Team wins final", "LFG 🚀" |

Rules of thumb:
- If two classes fit, pick the one a **risk manager** would care about most (credit > geopolitical > macro > commodity > regulatory > M&A > corporate > product).
- An analyst downgrade of a **stock** is `earnings_corporate`; a downgrade of **debt / credit rating** is `credit_event`.
- Judge only what the text says; don't use outside knowledge of what happened later.

## Column `sentiment` — `neg`, `neu` or `pos`
Perspective: **is this news good or bad for financial markets and for the credit/equity holders of the entities mentioned?**
- `neg`: bad news for markets / the subject (war escalation, price shock for consumers, losses, downgrades, rate-hike pressure on asset prices).
- `pos`: good news (strong results, de-escalation, ceasefire progress, rally).
- `neu`: factual/no clear direction, or mixed and roughly balanced.
- A commodity price spike is **`neg`** (a cost shock for the broad economy) unless the item is explicitly about a producer's profits.

## Column `notes` (optional)
Write anything ambiguous, e.g. "could be macro or geopolitical", "sarcasm", "not English".

## Human verification of the test sets
The test labels (W1 test, 150 items; W3 test, 120 items) are checked by a person in two stages. Use the same class and sentiment definitions as above.

1. **Stage A (blind), `data/eval/human_verify_stage_a.csv`, 50 items.** A seeded random 25 items from each test set, with no other label shown. Fill `event_class` and `sentiment` from scratch. These answers measure how often the LLM annotator agrees with a person, with no anchoring.
2. **Stage B (confirm or correct), `data/eval/human_verify_stage_b.csv`, the remaining items.** The LLM label is shown in `llm_event_class` and `llm_sentiment` and pre-filled in `event_class` and `sentiment`. Change the pre-filled columns where you disagree and add a short note. Put `y` in `reviewed` for every row you have checked, including rows you leave unchanged; rows without `y` are not counted as human-verified.

The final test labels are the human answers from both stages. Development labels (`labels_w1_dev_sheet.csv`, 200 items) stay LLM-only and are used for tuning; the test sets are never used for tuning.

## What happens next
**How these labels were actually produced:** both sheets were labelled by an automated LLM annotation pass using this guide verbatim, in two separate chat sessions, without human review. See `docs/evaluation.md`.

`scripts/evaluate.py` joins your labels with the model outputs through the key file and reports event-class macro-F1 (vs a majority-class baseline), sentiment accuracy for VADER-with-finance-lexicon vs FinBERT, and the repeat-labelling agreement (Cohen's κ) on the 30 re-labelled items.
