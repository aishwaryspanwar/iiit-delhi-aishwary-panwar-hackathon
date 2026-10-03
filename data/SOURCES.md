# Data Sources, Provenance and Licences

Everything needed to run the prototype is in this folder; nothing is downloaded at runtime.
Raw downloads live in `data/raw/` (gitignored) and are reproducible with the fetch scripts below.
No real or confidential client data is used anywhere. The portfolio and every rating, PD and sensitivity in it is synthetic.

| File | What it is | Source | Licence / terms | How to regenerate |
|---|---|---|---|---|
| `sources/w1/gdelt_headlines.csv` | News headlines, 2022-02-10 → 2022-03-24, from GDELT GKG 2.1 (the `:00` file of every hour). Kept only allow-listed financial/general news outlets whose GKG themes are finance, economy, sanctions, energy or conflict related, with title ≥ 25 characters. Columns: GKG record id, crawl timestamp (UTC), outlet, URL, page title. | The GDELT Project, http://data.gdeltproject.org/gdeltv2/ | GDELT Terms of Use: unlimited, unrestricted use; redistribution allowed with citation and a link to https://www.gdeltproject.org/. **Citation:** The GDELT Project, https://www.gdeltproject.org/. Headlines remain the property of their publishers; only titles and links are stored, never article bodies. | `python -m scripts.fetch_gdelt` |
| `sources/w1/tweets.csv` | Tweets about 25 stock tickers in the same window, **replayed historical data** (not live X/Twitter). Text is sanitised: URLs removed, user handles replaced with `@user`. Columns: source row id, timestamp (UTC), text. The uploader's ticker column is dropped because it is unreliable (identical tweets appear under MSFT, PG and AMZN). | Kaggle: `equinxx/stock-tweets-for-sentiment-analysis-and-prediction` (Hanna Yukhymenko), file `stock_tweets.csv` | CC0: Public Domain (as declared by the uploader). Tweet authors retain rights in their own words; we store only the sanitised subset needed for the window. | Download `stock_tweets.csv` from Kaggle into `data/raw/`, then `python -m scripts.fetch_tweets` |
| `market/returns_daily.csv` | Daily simple returns (2022-01 → 2022-04) for the 25 tweet tickers, S&P 500, VIX, sector and bond ETFs; `^TNX_change_bp` is the daily change of the US 10-year yield in basis points. Used only for evaluation (impact sanity check) and calibration notes. | Yahoo Finance via `yfinance` | Yahoo's terms restrict redistribution of raw price data, so only **derived returns** are committed. | `python -m scripts.fetch_prices` |
| `portfolio/portfolio_v1.csv` | Synthetic wholesale-banking book: 12 loans, 12 bonds, 6 interest-rate swaps, 10 equities. Credit positions use **synthetic obligor names** (e.g. `Obligor-ENR-RU-01`); equities use real public tickers with illustrative betas. | Generated from `config/portfolio.yaml` (seed 20220224) | Synthetic, ours (MIT). | `python -m src.stress.portfolio_gen` |
| `stub/stub_documents.csv` | 25 hand-written sample items (18 news-style, 7 tweet-style) used for the stub vertical slice and tests. Original wording, not copied from any publication. | Written for this project | Ours (MIT) | — |
| `processed/<dataset>/signals_v1.jsonl` | **The engine's output contract**: one structured risk signal per de-duplicated item (sentiment, event class, impact with components, entities, scope). | Built by the engine | Derived | `python -m src.pipeline --dataset w1` |
| `processed/<dataset>/events_v1.jsonl` | Event clusters (class × scope target × day) with cluster-level impact and breadth. | Built by the engine | Derived | same |
| `processed/<dataset>/stress_results_v1.json` | Module B output: trigger decision for every event and full stress results for triggered ones. | Built by Module B | Derived | same |
| `../config/rating_table.csv` | Illustrative 1-year PDs and credit spreads by rating notch. | Illustrative values, monotone in rating, broadly in line with public long-run corporate default averages; PD floor 0.03% (Basel). | Ours | — |

## Assumptions about the data
- GDELT timestamps are **crawl times** (when GDELT processed the article), not publisher times; typically within an hour of publication.
- Hourly sampling (1 of every 4 GKG files) is a deliberate volume control; every event that is widely reported appears many times across the hour samples, so cluster breadth is preserved in relative terms.
- The tweet dataset is dominated by a few tickers (TSLA, TSM) and covers no banks or energy names, so tweets mostly produce single-name and earnings signals; **news drives almost all stress triggers**.
- Only English titles are used.
