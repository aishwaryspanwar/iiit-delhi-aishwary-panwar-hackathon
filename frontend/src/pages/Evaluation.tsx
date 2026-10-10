import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { dateTime, integer, percent, usdMillions } from "../lib/format";
import type { ClassReport, Correlation, DetectionQuality, Evaluation as EvaluationData } from "../lib/types";
import { EmptyState, ErrorState, LoadingBlock, Panel, Stat, cx } from "../components/ui";

const SPLIT_TEXT: Record<string, string> = { w1_dev: "W1 development", w1_test: "W1 test", w3_test: "W3 test" };
const WINDOW_TEXT: Record<string, string> = { w1: "W1 (Feb-Mar 2022)", w3: "W3 (Sep 2022)", n1: "N1 (Aug-Sep 2026)", pooled: "All windows" };
const TH = "caption py-2.5 pr-4 text-left font-medium";
const TD = "num py-2.5 pr-4 text-right";

function ci(range?: [number, number]): string {
  return range ? `${range[0].toFixed(2)}-${range[1].toFixed(2)}` : "";
}

function ScoreCell({ report, metric }: { report: ClassReport; metric: "accuracy" | "macro_f1" }) {
  const range = metric === "accuracy" ? report.accuracy_ci95 : report.macro_f1_ci95;
  return (
    <td className={TD}>
      <span className="font-semibold text-ink">{report[metric].toFixed(2)}</span>
      {range && <span className="ml-1.5 text-[11.5px] text-ink-3">[{ci(range)}]</span>}
    </td>
  );
}

function ClassificationTable({ data }: { data: EvaluationData }) {
  const splits = Object.entries(data.metrics?.splits ?? {});
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-[13px]">
        <caption className="sr-only">Classification and sentiment scores with 95% bootstrap intervals</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Split</th>
            <th scope="col" className={cx(TH, "text-right")}>Items (human-verified)</th>
            <th scope="col" className={cx(TH, "text-right")}>Event class macro-F1</th>
            <th scope="col" className={cx(TH, "text-right")}>Keyword baseline</th>
            <th scope="col" className={cx(TH, "text-right")}>Majority baseline</th>
            <th scope="col" className={cx(TH, "text-right")}>FinBERT macro-F1</th>
            <th scope="col" className={cx(TH, "text-right")}>VADER macro-F1</th>
          </tr>
        </thead>
        <tbody>
          {splits.map(([name, split]) => {
            const r = split.representative;
            return (
              <tr key={name} className="border-b border-line last:border-b-0">
                <th scope="row" className="py-2.5 pr-4 text-left font-medium text-ink">
                  {SPLIT_TEXT[name] ?? name}
                  <div className="text-[11.5px] font-normal text-ink-3">{split.role}</div>
                </th>
                <td className={TD}>
                  {integer(r.n)} ({integer(r.human_verified)})
                </td>
                <ScoreCell report={r.event_class} metric="macro_f1" />
                <td className={cx(TD, "text-ink-3")}>{r.event_class_naive_keywords.macro_f1.toFixed(2)}</td>
                <td className={cx(TD, "text-ink-3")}>{r.event_class.majority_macro_f1.toFixed(2)}</td>
                <ScoreCell report={r.sentiment_finbert} metric="macro_f1" />
                <td className={cx(TD, "text-ink-3")}>{r.sentiment_vader.macro_f1.toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CorrelationCell({ value }: { value: Correlation }) {
  return (
    <td className={TD}>
      <span className="font-semibold text-ink">{value.rho.toFixed(2)}</span>
      <span className="ml-1.5 text-[11.5px] text-ink-3">[{ci(value.ci95)}]</span>
    </td>
  );
}

function ImpactMarketTable({ data }: { data: EvaluationData }) {
  const rows = Object.entries(data.metrics?.impact_vs_market ?? {});
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-[13px]">
        <caption className="sr-only">Spearman correlation of daily maximum event impact with market moves</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Window</th>
            <th scope="col" className={cx(TH, "text-right")}>Days</th>
            <th scope="col" className={cx(TH, "text-right")}>|S&P 500 move|</th>
            <th scope="col" className={cx(TH, "text-right")}>VIX change</th>
            <th scope="col" className={cx(TH, "text-right")}>|10y yield change|</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([window, values]) => (
            <tr key={window} className="border-b border-line last:border-b-0">
              <th scope="row" className="py-2.5 pr-4 text-left font-medium text-ink">{WINDOW_TEXT[window] ?? window}</th>
              <td className={TD}>{values.abs_sp500.n}</td>
              <CorrelationCell value={values.abs_sp500} />
              <CorrelationCell value={values.vix_change} />
              <CorrelationCell value={values.abs_rate_change} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function quality(q: DetectionQuality): string {
  const p = q.precision === null ? "n/a" : percent(q.precision, 0, false);
  const r = q.recall === null ? "n/a" : percent(q.recall, 0, false);
  return `${q.flags} flags, precision ${p}, recall ${r}`;
}

function TriggerTable({ data }: { data: EvaluationData }) {
  const rows = Object.entries(data.metrics?.trigger_quality ?? {});
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] border-collapse text-[13px]">
        <caption className="sr-only">Trigger precision and recall against market stress days, compared with naive triggers</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Window</th>
            <th scope="col" className={cx(TH, "text-right")}>Stress days / base rate</th>
            <th scope="col" className={TH}>Engine alerts</th>
            <th scope="col" className={TH}>Impact &gt; 7, no gates</th>
            <th scope="col" className={TH}>Headline-volume spike</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([window, q]) => (
            <tr key={window} className="border-b border-line last:border-b-0">
              <th scope="row" className="py-2.5 pr-4 text-left font-medium text-ink">{WINDOW_TEXT[window] ?? window}</th>
              <td className={TD}>
                {q.stress_days} of {q.trading_days} ({q.base_rate === null ? "n/a" : percent(q.base_rate, 0, false)})
              </td>
              <td className="py-2.5 pr-4 font-medium text-ink">{quality(q.engine_alerts)}</td>
              <td className="py-2.5 pr-4 text-ink-2">{quality(q.impact_above_7_without_gates)}</td>
              <td className="py-2.5 pr-4 text-ink-2">{quality(q.naive_headline_volume_spike)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BacktestTable({ data }: { data: EvaluationData }) {
  const windows = Object.entries(data.backtest?.windows ?? {});
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-[13px]">
        <caption className="sr-only">Stressed against realised P&L of the liquid sleeve after each trigger</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Trigger</th>
            <th scope="col" className={cx(TH, "text-right")}>Stressed</th>
            <th scope="col" className={cx(TH, "text-right")}>Realised, 1 day</th>
            <th scope="col" className={cx(TH, "text-right")}>Realised, 5 days</th>
          </tr>
        </thead>
        <tbody>
          {windows.flatMap(([window, result]) =>
            result.triggers.map((t) => (
              <tr key={`${window}-${t.cluster_id}`} className="border-b border-line last:border-b-0">
                <th scope="row" className="py-2.5 pr-4 text-left font-normal text-ink-2">
                  <span className="font-medium text-ink">{WINDOW_TEXT[window] ?? window}</span> {t.cluster_id.split("|").slice(1).join(", ")}
                  <div className="text-[11.5px] text-ink-3">detected {dateTime(t.detected_at)}</div>
                </th>
                <td className={cx(TD, "text-loss")}>{usdMillions(t.stressed_sleeve_pnl, 1, true)}</td>
                <td className={cx(TD, (t.realised_sleeve_pnl_1d ?? 0) < 0 ? "text-loss" : "text-gain")}>{t.realised_sleeve_pnl_1d === null ? "n/a" : usdMillions(t.realised_sleeve_pnl_1d, 1, true)}</td>
                <td className={cx(TD, (t.realised_sleeve_pnl_5d ?? 0) < 0 ? "text-loss" : "text-gain")}>{t.realised_sleeve_pnl_5d === null ? "n/a" : usdMillions(t.realised_sleeve_pnl_5d, 1, true)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Evaluation() {
  const state = useAsync((signal) => api.evaluation(signal), []);
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  if (!state.data) return <LoadingBlock rows={8} label="Loading evaluation" />;
  const data = state.data;
  if (!data.metrics) return <EmptyState title="No evaluation yet" body="Run python -m scripts.evaluate to produce data/eval/metrics.json." />;
  const agreement = data.metrics.llm_vs_human_blind;
  const lead = data.metrics.alert_lead_times;
  const leadWindows = Object.entries(lead).filter(([, v]) => v.alerts > 0);
  return (
    <div className="flex flex-col gap-5">
      <section className="panel grid grid-cols-2 gap-6 px-6 py-6 lg:grid-cols-4">
        <Stat label="Engine version" value={data.metrics.engine_version} sub={`config ${data.metrics.config_hash}`} size="sm" />
        <Stat
          label="LLM vs human (blind)"
          value={agreement.n ? percent(agreement.event_class_agreement ?? 0, 0, false) : "pending"}
          sub={agreement.n ? `event class, n=${agreement.n}, kappa ${(agreement.event_class_kappa ?? 0).toFixed(2)}` : "human verification in progress"}
          size="sm"
        />
        <Stat
          label="Throughput"
          value={data.benchmark ? `${integer(Math.round(data.benchmark.items_per_second_vader_pipeline))}/s` : "n/a"}
          sub={data.benchmark?.finbert_items_per_second_cpu ? `FinBERT ${data.benchmark.finbert_items_per_second_cpu}/s on CPU` : "items per second, CPU"}
          size="sm"
        />
        <Stat
          label="Alert lead time"
          value={leadWindows.length ? `${leadWindows[0][1].median_hours_before_end_of_day_batch?.toFixed(1)} h` : "n/a"}
          sub="median, before an end-of-day batch run"
          size="sm"
        />
      </section>
      <Panel title="Classification and sentiment" description="Scored on held-out items; brackets are 95% bootstrap intervals. Test sets were never used for tuning.">
        <ClassificationTable data={data} />
      </Panel>
      <Panel title="Does impact track the market?" description="Spearman rank correlation of the daily maximum event impact with same-day market moves (bracket: 95% bootstrap interval)">
        <ImpactMarketTable data={data} />
      </Panel>
      <Panel title="Trigger quality" description={data.metrics.definitions.stress_day + ". " + data.metrics.definitions.hit + "."}>
        <TriggerTable data={data} />
      </Panel>
      <Panel title="Stress backtest" description="Stressed P&L of the liquid sleeve (equities and bond ETF proxies) against realised moves after each trigger. A stress scenario is a severe-but-plausible bound, not a forecast.">
        {data.backtest ? <BacktestTable data={data} /> : <EmptyState title="No backtest yet" body="Run python -m scripts.backtest_stress." />}
      </Panel>
    </div>
  );
}
