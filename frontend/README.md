# Ripple web app

The React frontend and the only user interface for the Python engine. It reads the files in `data/processed/<dataset>/` (the replay windows and the `live` feed) through a thin JSON API that calls the engine modules. React never re-implements scoring, triggers or valuation.

```
config/ + data/processed/*.jsonl.gz + stress_results_v1.json + data/eval/*.json
                     │
        Python core (src/riskengine, src/stream, src/stress)
                         │
          thin JSON API (src/api, stdlib http.server)
          port 8000, read-only + POST /api/score
          serves frontend/dist after npm run build
                         │
          React + Vite (frontend/), dev server port 5173
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

Optional terminal 3, from the repository root (live feed; the `live` dataset appears in the dataset menu after the first poll):

```bash
python -m scripts.live_gdelt
```

Single-process alternative: run `npm run build` once. `python -m src.api` then also serves the built app at http://127.0.0.1:8000/.

Other scripts: `npm run typecheck`, `npm test` (Vitest), `npm run preview`. To use a different API port, run `python -m src.api --port 8100` and start Vite with `RISK_API_PORT=8100`.

## API surface (`src/api`)

| Method | Path | Backed by |
|---|---|---|
| GET | `/api/health`, `/api/datasets`, `/api/meta` | `src.pipeline` dataset registry (with `live` and `updated_at`); taxonomy, impact and shock configs |
| GET | `/api/datasets/{id}/summary` | per-day aggregates of `signals_v1` / `events_v1`; trigger decisions |
| GET | `/api/datasets/{id}/events`, `/events/{cluster_id}` | `events_v1` + status from `src.stress.trigger.event_status` |
| GET | `/api/datasets/{id}/signals?until&class&source&sentiment&min_impact&q&sort&offset&limit` | `signals_v1`, filtered and paginated server-side (W1 has 34k signals) |
| GET | `/api/datasets/{id}/signals/{signal_id}` | signal record + its cluster, decision and run |
| GET | `/api/datasets/{id}/stress`, `/stress/{cluster_id}` | `stress_results_v1.json` runs and decisions, unchanged |
| GET | `/api/datasets/{id}/alerts` | `alerts_v1` from the as-of stream, with the stress P&L of each alert |
| GET | `/api/datasets/{id}/geo?until&days` | per-country headline counts, mean sentiment, peak impact and top headlines; a signal is placed on every country it names, or the home country of a named central bank or index |
| POST | `/api/score` | `score_single_text` → `what_if_event` → `condition_checks` → `run_stress` (the engine path, unchanged) |

The API binds to 127.0.0.1. It validates every query and body field (text ≤ 300 chars, outlets 1–30, volume from the fixed option list), caps bodies at 8 KB, gzips large responses and returns JSON errors without stack traces. It never fetches URLs. User text is rendered as plain text only.

## Screens

- **Overview:** replay bar with play/pause and trigger markers; an interactive world map of headlines by country (bubble size = coverage, colour = mean sentiment, orange ring = a headline above the trigger threshold) with a risk gauge, most-covered list and key figures; the event timeline as a dot matrix (one column per period, lit to the riskiest event's impact, dots above the trigger line in amber or red); real-time alerts with their lead over an end-of-day batch; latest high-impact events; signals by class; the latest stress test with its causal chain; market mood.
- **Signal feed:** search plus class, source, sentiment and impact filters, following the replay date. Clicking a row opens the explainability drawer: matched rules with their patterns, impact components × weights, entities, provenance, the cluster's trigger checks with their actual values, and a link to the stress run.
- **Stress test:** triggered-event picker, causal chain (event → classification → impact → scenario → shock → portfolio), before/after values, P&L by asset class, factor waterfall, value by asset class, credit losses and capital, severity curve, shocks applied, trigger checks (the engine's full explanation is behind a toggle), positions, and the trigger funnel.
- **Try a headline:** live scoring, what-if outlets and volume, trigger checks, and a Module B preview. The page scrolls to the result after scoring.

## Experience

- **Walkthrough:** a six-step guided tour opens on the first visit (stored in `localStorage` as `risk-engine-tour`); it can be skipped at any step with the button, the close icon or Esc, and replayed from the **?** button in the header.
- **Loading:** a full-page skeleton that matches each page's layout is shown while data loads; tables, the stress column and the causal chain have matching in-place skeletons.
- **Responsive:** built for desktop widths from 1024 px to 2560 px and wider. The page width grows to 1680 px from 1800 px and to 2000 px from 2200 px (`--page-max` in `src/index.css`), and short screens get a tighter header.

## Design system

- **Brand:** the Ripple mark lives in `src/assets/ripple-mark.svg` (exported from the `brand/mark` Figma component) and is drawn in the theme's ink colour, so it reads in both themes. The favicon (`src/assets/ripple-favicon.svg`) is a light mark on a dark tile, so it shows on any tab bar, and it is hashed by the build.
- **Surfaces:** glass tiles (blur, hairline border) on a teal-black gradient with a light beam; top navigation in a glass pill.
- **Accents:** orange #FF6703 for actions, focus and the replay cursor; teal #64A795 for emphasis bars, tags and status; white pills for the current selection.
- **Typography:** Google Sans Flex everywhere, in two weights: Regular (400) for text and SemiBold (600) for titles, labels and key figures.
- **Light mode:** designed separately, not inverted.

## Presentation-only conventions

- **Risk bands** are a display banding of the engine's 1–10 impact score: low below 4, moderate from 4 to the trigger threshold, high above the threshold (7 in `config/shocks.yaml`), critical from (threshold + 10) / 2. They do not affect any calculation.
- **Colours:** losses are red and gains blue. Red against green fails colour-vision separation (checked with the dataviz palette validator), while red against blue passes in both themes. Status also has a shape (◆ triggered, ▲ blocked, ○ below) and a text label; risk bands carry a level glyph and a word.
- **Live dataset:** the header shows when the feed was last rebuilt, and the app re-fetches it every minute; the API reloads a dataset whenever its files change.
- **Theme:** dark by default, light available. The choice is stored in `localStorage` (`risk-engine-theme`).

## Assets

- **Fonts:** [Google Sans Flex](https://fontsource.org/fonts/google-sans-flex), Regular and SemiBold only, bundled from `@fontsource/google-sans-flex` (SIL Open Font License) so no CDN is needed offline.
- **Images:** none. The interface uses no stock imagery.
