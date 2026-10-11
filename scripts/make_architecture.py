import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from src.riskengine.config import REPO_ROOT

OUTPUT = REPO_ROOT / "docs" / "architecture.png"
INK = "#1f2933"
MUTED = "#52606d"
LINE = "#9aa5b1"
FILLS = {"source": "#e6f0fa", "engine": "#e8f5ec", "stream": "#fff4e0", "store": "#f0ecfa", "stress": "#fdeaea", "ui": "#eef2f5", "eval": "#f7f7f2", "config": "#f7f7f2"}


def box(ax, x, y, w, h, title, lines, kind, title_size=13):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018", linewidth=1.4, edgecolor=LINE, facecolor=FILLS[kind]))
    ax.text(x + 0.012, y + h - 0.03, title, fontsize=title_size, fontweight="bold", color=INK, va="top")
    for index, line in enumerate(lines):
        ax.text(x + 0.012, y + h - 0.075 - index * 0.036, line, fontsize=10.2, color=MUTED, va="top")


def arrow(ax, start, end, label=None, offset=(0.0, 0.012)):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, linewidth=1.6, color=INK, shrinkA=2, shrinkB=2))
    if label:
        ax.text((start[0] + end[0]) / 2 + offset[0], (start[1] + end[1]) / 2 + offset[1], label, fontsize=9.5, color=MUTED, ha="center", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})


def draw(path: Path) -> None:
    fig = plt.figure(figsize=(20, 10), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 2.0)
    ax.set_ylim(0, 1.0)
    ax.axis("off")
    ax.text(0.02, 0.975, "Ripple: event-driven risk signals and portfolio stress testing, architecture and data flow", fontsize=18, fontweight="bold", color=INK, va="top")
    ax.text(0.02, 0.94, "CPU-only and deterministic; replay windows run offline, live mode polls GDELT. Every number is traceable to a rule, a weight or a data file.", fontsize=11.5, color=MUTED, va="top")
    box(ax, 0.02, 0.55, 0.28, 0.35, "Text sources", ["GDELT GKG 2.1 headlines", "windows W1, W3, N1 (hourly sample)", "live 15-minute feed (scripts/live_gdelt)", "Kaggle stock tweets (W1, W3)", "replayed, sanitised"], "source")
    box(ax, 0.02, 0.28, 0.28, 0.23, "Market data", ["derived daily returns (yfinance)", "analogue episodes 2011-2020", "used for calibration and evaluation,", "never in scoring"], "source")
    box(ax, 0.02, 0.03, 0.28, 0.21, "Protocol", ["W1: development and calibration", "W3: untouched shock test", "N1: untouched calm test", "config frozen before W3/N1 scoring"], "config")
    box(ax, 0.35, 0.47, 0.32, 0.43, "Risk engine  src/riskengine", ["1  clean, de-duplicate (keeps outlets)", "2  241 entities and cashtags -> scope", "3  weighted rules -> 9 event classes,", "    exclusions and credit direction", "4  sentiment: FinBERT (build default),", "    VADER + lexicon (live fallback)", "5  item impact 1-10, components stored", "-> one schema-validated signal per item"], "engine")
    box(ax, 0.72, 0.47, 0.32, 0.43, "As-of stream  src/stream", ["hourly ticks, rolling 24h window per", "(class, scope, primary target)", "uses only data up to each tick", "baseline: same hour, previous 7 days", "impact: severity, breadth, abnormal volume", "checks: class, impact > 7, confidence,", "sentiment, direction, outlets, mentions,", "warm-up, 72h cooldown per target"], "stream")
    box(ax, 0.35, 0.03, 0.69, 0.38, "Configuration  config/", ["no magic numbers in code; the config hash is stamped into every build", "taxonomy rules and exclusions, entity lexicon, impact weights,", "sampling rates, trigger thresholds,", "shock scenarios with their calibration sources, contagion links,", "rating table (PDs, spreads, Basel III risk weights),", "portfolio recipe and beta-estimation window"], "config")
    box(ax, 1.09, 0.60, 0.40, 0.30, "Outputs  data/processed/", ["one folder per window (W1, W3, N1, stub) and live", "signals_v1.jsonl.gz    one per item", "events_v1.jsonl.gz     daily clusters", "alerts_v1.jsonl.gz     detection time, checks", "stress_results_v1.json   Module B runs", "JSON Schemas are the contract"], "store")
    box(ax, 1.09, 0.03, 0.40, 0.50, "Module B  src/stress", ["scenarios calibrated on analogue episodes", "scope-aware shocks and contagion map", "bonds: rate/spread duration, convexity", "loans: IFRS 9 staging, lifetime ECL", "swaps DV01, equities beta, option greeks", "capital: Basel III standardised RWA", "P&L attribution sums exactly to total", "severity curve for impact 7 to 10"], "stress")
    box(ax, 1.54, 0.60, 0.44, 0.30, "Consumers", ["read-only JSON API  src/api  :8000", "Ripple web app  frontend/  (prebuilt, served by the API)", "live dataset, rebuilt every 15 minutes", "live headline scoring and what-if"], "ui")
    box(ax, 1.54, 0.03, 0.44, 0.50, "Evaluation  scripts/", ["annotated test labels (W1, W3)", "bootstrap 95% CIs; majority and keyword", "baselines; FinBERT vs VADER", "impact vs market (Spearman with CIs)", "trigger precision/recall vs naive triggers", "alert lead time, throughput benchmark", "stress backtest vs realised moves", "freeze check: scripts/verify_freeze", "canary set of 44 well-known headlines"], "eval")
    arrow(ax, (0.30, 0.72), (0.35, 0.72), "text", (0.0, 0.025))
    arrow(ax, (0.67, 0.68), (0.72, 0.68), "signals", (0.0, 0.025))
    arrow(ax, (1.04, 0.78), (1.09, 0.78), "events", (0.0, 0.025))
    arrow(ax, (1.04, 0.52), (1.09, 0.44), "alerts")
    arrow(ax, (1.29, 0.53), (1.29, 0.60), None)
    arrow(ax, (1.49, 0.75), (1.54, 0.75), "API", (0.0, 0.025))
    arrow(ax, (1.49, 0.28), (1.54, 0.28), "runs", (0.0, 0.025))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    draw(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
