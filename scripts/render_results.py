from datetime import datetime, timedelta

from src.riskengine.config import DATA_DIR, REPO_ROOT
from src.riskengine.io import read_json

RESULTS_PATH = REPO_ROOT / "docs" / "results.md"
EVAL_DIR = DATA_DIR / "eval"
SPLIT_TEXT = {"w1_dev": "W1 development", "w1_test": "W1 test", "w3_test": "W3 test"}
WINDOW_TEXT = {"w1": "W1, Feb-Mar 2022 (development)", "w3": "W3, Sep 2022 (test, shock)", "n1": "N1, Aug-Sep 2026 (test, calm)", "pooled": "All windows pooled"}
IST = timedelta(hours=5, minutes=30)
CLASS_TEXT = {"geopolitical": "Geopolitical", "macroeconomic": "Macroeconomic", "credit_event": "Credit event", "commodity_energy": "Commodity/energy", "regulatory": "Regulatory"}


def ist(value: str) -> str:
    if len(value) == 10:
        return value
    return (datetime.fromisoformat(value.replace("Z", "+00:00")) + IST).strftime("%Y-%m-%d %H:%M")


def interval(values) -> str:
    return f"{values[0]:.2f}-{values[1]:.2f}" if values else "n/a"


def pct(value) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def musd(value) -> str:
    return "n/a" if value is None else f"{value / 1e6:+,.1f}m"


def classification_section(metrics: dict) -> list[str]:
    lines = [
        "## 1. Classification and sentiment",
        "",
        "Representative (stratified) items only. Brackets are 95% bootstrap intervals. The development split was used for tuning; the test labels were never used to write or tune rules.",
        "",
        "| Split | Items | Human-verified | Event class macro-F1 | Keyword baseline | Majority baseline | Event class accuracy | FinBERT macro-F1 | VADER macro-F1 | Always-neutral accuracy | FinBERT accuracy |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for split, report in metrics["splits"].items():
        r = report["representative"]
        ec, fb, vd = r["event_class"], r["sentiment_finbert"], r["sentiment_vader"]
        lines.append(
            f"| {SPLIT_TEXT.get(split, split)} | {r['n']} | {r['human_verified']} | **{ec['macro_f1']:.2f}** [{interval(ec.get('macro_f1_ci95'))}] | {r['event_class_naive_keywords']['macro_f1']:.2f} | {ec['majority_macro_f1']:.2f} "
            f"| {ec['accuracy']:.2f} [{interval(ec.get('accuracy_ci95'))}] | **{fb['macro_f1']:.2f}** [{interval(fb.get('macro_f1_ci95'))}] | {vd['macro_f1']:.2f} | {fb['majority_accuracy']:.2f} | {fb['accuracy']:.2f} |"
        )
    blind = metrics["llm_vs_human_blind"]
    lines += ["", "**Annotator check.** " + (
        f"On {blind['n']} items labelled blind by a person, the LLM annotator agreed on the event class {blind['event_class_agreement']:.0%} of the time (Cohen's kappa {blind['event_class_kappa']:.2f}) and on sentiment {blind['sentiment_agreement']:.0%} (kappa {blind['sentiment_kappa']:.2f})."
        if blind.get("n") else "Human verification of the test labels is in progress; until it completes, test labels are the LLM annotation."
    ), ""]
    return lines


def market_section(metrics: dict) -> list[str]:
    lines = [
        "## 2. Does impact track the market?",
        "",
        "Spearman rank correlation of the daily maximum event impact (stress-relevant classes, after warm-up) with same-day market moves. Brackets are 95% bootstrap intervals over days.",
        "",
        "| Window | Trading days | vs abs. S&P 500 move | vs VIX change | vs abs. 10y yield change |",
        "|---|---|---|---|---|",
    ]
    for window, values in metrics["impact_vs_market"].items():
        cells = " | ".join(f"{values[k]['rho']:+.2f} [{interval(values[k]['ci95'])}]" for k in ("abs_sp500", "vix_change", "abs_rate_change"))
        lines.append(f"| {WINDOW_TEXT.get(window, window)} | {values['abs_sp500']['n']} | {cells} |")
    return lines + [""]


def trigger_section(metrics: dict) -> list[str]:
    lines = [
        "## 3. Trigger quality against market stress days",
        "",
        f"A stress day is a day with {metrics['definitions']['stress_day'].split('or')[0].strip().lower()} or a VIX jump of more than 10%. {metrics['definitions']['hit'].capitalize()}.",
        "",
        "| Window | Stress days (base rate) | Engine alerts: flags, precision, recall | Impact > 7 without gates | Naive headline-volume spike | Fire every day |",
        "|---|---|---|---|---|---|",
    ]
    for window, q in metrics["trigger_quality"].items():
        cell = lambda d: f"{d['flags']}, {pct(d['precision'])}, {pct(d['recall'])}"
        lines.append(f"| {WINDOW_TEXT.get(window, window)} | {q['stress_days']} of {q['trading_days']} ({pct(q['base_rate'])}) | **{cell(q['engine_alerts'])}** | {cell(q['impact_above_7_without_gates'])} | {cell(q['naive_headline_volume_spike'])} | {cell(q['naive_fire_every_day'])} |")
    lines += ["", "**Lead time.** Alerts come from the hourly stream, using only data available at the time.", "", "| Window | Alerts | Median hours before an end-of-day batch run | Share before the US close |", "|---|---|---|---|"]
    for window, lead in metrics["alert_lead_times"].items():
        hours = "n/a" if lead["median_hours_before_end_of_day_batch"] is None else f"{lead['median_hours_before_end_of_day_batch']:.1f}"
        lines.append(f"| {WINDOW_TEXT.get(window, window)} | {lead['alerts']} | {hours} | {pct(lead['share_before_us_close'])} |")
    return lines + [""]


def windows_section(windows: dict) -> list[str]:
    lines = ["## 4. Stress tests by window", ""]
    for window, summary in windows.items():
        market = summary["market"]
        lines += [
            f"### {WINDOW_TEXT.get(window, window)}",
            "",
            f"{summary['signals']:,} signals, {summary['clusters']:,} daily event records, {summary['clusters_above_threshold']} above impact 7, **{summary['stress_tests_triggered']} stress tests**. "
            f"Entity coverage {summary['entity_coverage']:.0%}. S&P 500: annualised volatility {market['sp500_annualised_volatility']:.1%}, worst day {market['sp500_worst_day']:+.2%}.",
            "",
        ]
        if summary["runs"]:
            lines += ["| Detected (IST) | Class | Target | Impact at detection | Portfolio P&L |", "|---|---|---|---|---|"]
            for run in summary["runs"]:
                detected = ist(run["detected_at"] or run["date"])
                lines.append(f"| {detected} | {CLASS_TEXT.get(run['class'], run['class'])} | {', '.join(t.split(':', 1)[1] for t in run['scope_targets'][:2]) or 'none'} | {run['impact']:.1f} | {musd(run['pnl'])} ({run['pnl_pct']:+.2%}) |")
            lines.append("")
    return lines


def backtest_section(backtest: dict) -> list[str]:
    lines = [
        "## 5. Stress backtest",
        "",
        f"Liquid sleeve of {backtest['sleeve']['positions']} positions ({backtest['sleeve']['value'] / 1e6:,.0f}m: equities and bond ETF proxies {', '.join(p for p in backtest['sleeve']['proxies'] if p in ('LQD', 'HYG', 'IEF'))}). "
        "A stress scenario is a severe-but-plausible bound, not a forecast: coverage is the share of triggers where the realised loss stayed within the stressed loss.",
        "",
        "| Window | Horizon | Triggers | Coverage | Realised negative | Mean stressed | Mean realised | Share of all days negative |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for window, result in backtest["windows"].items():
        for horizon, s in result["summary"].items():
            base = result["unconditional_all_days"][horizon]
            lines.append(f"| {WINDOW_TEXT.get(window, window)} | {horizon} | {s['triggers']} | {pct(s['coverage_realised_loss_within_stress'])} | {pct(s['direction_hit_realised_negative'])} | {musd(s['mean_stressed_pnl'])} | {musd(s['mean_realised_pnl'])} | {pct(base['share_negative'])} |")
    return lines + [""]


def benchmark_section(benchmark: dict) -> list[str]:
    seconds = benchmark["seconds"]
    return [
        "## 6. Throughput",
        "",
        f"On a laptop CPU ({benchmark['machine']['processor']}), the rule pipeline with VADER processes **{benchmark['items_per_second_vader_pipeline']:,.0f} items/s** end to end "
        f"({benchmark['deduplicated_items']:,} W1 items: clean {seconds['clean_and_dedup']}s, rules/entities/impact {seconds['rules_entities_impact']}s, stream {seconds['stream_clusters_alerts']}s). "
        f"FinBERT scores {benchmark.get('finbert_items_per_second_cpu', 'n/a')} items/s on the same CPU, so a 15-minute GDELT file is scored in well under a minute.",
        "",
    ]


def render() -> str:
    metrics = read_json(EVAL_DIR / "metrics.json")
    lines = [
        "# Results",
        "",
        f"Generated by `python -m scripts.render_results` from `data/eval/`. Engine {metrics['engine_version']}, configuration `{metrics['config_hash']}` (rules and lexicons extended after the `eval-freeze` tag, which froze engine 0.2.0 / configuration `4536f7568ed1` before W3 and N1 were first scored; for engine {metrics['engine_version']}, W3 and N1 are therefore not untouched tests). Times are India Standard Time.",
        "",
    ]
    lines += classification_section(metrics)
    lines += market_section(metrics)
    lines += trigger_section(metrics)
    windows_path, backtest_path, benchmark_path = EVAL_DIR / "window_comparison.json", EVAL_DIR / "backtest.json", EVAL_DIR / "benchmark.json"
    if windows_path.exists():
        lines += windows_section(read_json(windows_path))
    if backtest_path.exists():
        lines += backtest_section(read_json(backtest_path))
    if benchmark_path.exists():
        lines += benchmark_section(read_json(benchmark_path))
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    RESULTS_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
