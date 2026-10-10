# React frontend (Phase 6, parallel to Streamlit)

A second presentation layer over the same Python engine. Streamlit (`src/app/dashboard.py`) remains the reference UI. Both read the same precomputed files in `data/processed/<dataset>/` through the same Python modules. React never re-implements scoring, triggers or valuation.

```
config/ + data/processed/*.jsonl.gz + stress_results_v1.json
                     │
        Python core (src/riskengine, src/stress)
             │                         │
  Streamlit (src/app)        thin JSON API (src/api, stdlib http.server)
   port 8501                  port 8000, read-only + POST /api/score
                                        │
                              React + Vite (frontend/), port 5173
                              /api proxied to 127.0.0.1:8000
```

## Run

Requires Node.js 20.19+ or 22.12+ (developed on 22.14). The Python setup is unchanged (`pip install -r requirements.txt`). The API uses only the standard library and existing engine modules.

Terminal 1, from the repository root (API):

```bash
python -m src.api            # http://127.0.0.1:8000/api/health
```

Terminal 2 (React dev server):

```bash
cd frontend
npm install
npm run dev                  # http://127.0.0.1:5173
```

Optional terminal 3, from the repository root (Streamlit reference, for side-by-side comparison):

```bash
streamlit run src/app/dashboard.py   # http://127.0.0.1:8501
```

Single-process alternative: run `npm run build` once. `python -m src.api` then also serves the built app at http://127.0.0.1:8000/.

Other scripts: `npm run typecheck`, `npm test` (Vitest), `npm run preview`. To use a different API port, run `python -m src.api --port 8100` and start Vite with `RISK_API_PORT=8100`.

## API surface (`src/api`)

| Method | Path | Backed by |
|---|---|---|
| GET | `/api/health`, `/api/datasets`, `/api/meta` | `src.pipeline` dataset registry; taxonomy, impact and shock configs |
| GET | `/api/datasets/{id}/summary` | per-day aggregates of `signals_v1` / `events_v1`; trigger decisions |
| GET | `/api/datasets/{id}/events`, `/events/{cluster_id}` | `events_v1` + status from `src.stress.trigger.event_status` |
| GET | `/api/datasets/{id}/signals?until&class&source&sentiment&min_impact&q&sort&offset&limit` | `signals_v1`, filtered and paginated server-side (W1 has 34k signals) |
| GET | `/api/datasets/{id}/signals/{signal_id}` | signal record + its cluster, decision and run |
| GET | `/api/datasets/{id}/stress`, `/stress/{cluster_id}` | `stress_results_v1.json` runs and decisions, unchanged |
| GET | `/api/portfolio` | `data/portfolio/portfolio_v1.csv` via `load_portfolio` |
| POST | `/api/score` | `score_single_text` → `what_if_event` → `condition_checks` → `run_stress` (same path as Streamlit's "Try a headline") |

The API binds to 127.0.0.1. It validates every query and body field (text ≤ 300 chars, outlets 1–30, volume from the fixed option list), caps bodies at 8 KB, gzips large responses and returns JSON errors without stack traces. It never fetches URLs. User text is rendered as plain text only.

## Screens

- **Overview:** replay clock with play/pause and trigger markers, plus a risk posture card (peak event impact over the trailing 72 h). Also: KPIs, the event-impact timeline, signal mix by class, latest high-impact events, sentiment, and the latest triggered stress test with its causal chain.
- **Signal feed:** search plus class, source, sentiment and impact filters, following the replay clock. Clicking a row opens the explainability drawer: matched rules with their patterns, impact components × weights, entities, provenance, the cluster's trigger checks with their actual values, and a link to the stress run.
- **Stress test:** triggered-event picker, the causal chain (event → classification → impact → scenario → shock → portfolio), before/after values, P&L by asset class, factor waterfall, before/after table by asset class, base vs applied shocks, trigger checks, the engine's explanation, sortable positions, and the trigger funnel.
- **Try a headline:** live scoring, what-if outlets and volume, trigger checks, and a Module B preview.
- **Methodology:** pipeline, dataset/build provenance, trigger settings, portfolio composition and scenario library.

## Design system

The visual system is recorded in [DESIGN.md](../DESIGN.md), with machine-readable tokens in `.impeccable/design.json`. In short:
- **Surfaces:** glass tiles (blur, hairline border) on a teal-black gradient with a light beam; top navigation in a glass pill.
- **Accents:** orange #FF6703 for actions, focus and the replay cursor; teal #64A795 for emphasis bars, tags and status; white pills for the current selection.
- **Typography:** Peace Sans for titles and key figures, Open Sauce Sans for everything else.
- **Light mode:** designed separately, not inverted.

## Presentation-only conventions

- **Risk bands** are a display banding of the engine's 1–10 impact score: low below 4, moderate from 4 to the trigger threshold, high above the threshold (7 in `config/shocks.yaml`), critical from (threshold + 10) / 2. They do not affect any calculation.
- **Colours:** losses are red and gains blue. Red against green fails colour-vision separation (checked with the dataviz palette validator), while red against blue passes in both themes. Status also has a shape (◆ triggered, ▲ blocked, ○ below) and a text label; risk bands carry a level glyph and a word.
- **Theme:** dark by default, light available. The choice is stored in `localStorage` (`risk-engine-theme`).

## Assets

- **Fonts:** [Peace Sans](https://fontsource.org/fonts/peace-sans) and [Open Sauce Sans](https://fontsource.org/fonts/open-sauce-sans), bundled from `@fontsource` (SIL Open Font License) so no CDN is needed offline. The packaged regular-weight Open Sauce `.woff2` is corrupt, so `src/assets/fonts/` serves its working `.woff` instead.
- **Sign glyphs:** a `unicode-range` fallback named "Risk Signs" maps + − × Σ to the platform sans, so signs match across both faces.
- **Images:** none. The interface uses no stock imagery.
