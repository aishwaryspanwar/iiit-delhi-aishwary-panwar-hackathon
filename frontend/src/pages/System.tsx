import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { basisPoints, day, integer, percent, signed, usdMillions } from "../lib/format";
import { ASSET_TEXT, CHECK_ORDER, SOURCE_TEXT } from "../lib/risk";
import type { EventClass } from "../lib/types";
import { HBarList } from "../components/charts";
import { ErrorState, KeyValue, LoadingBlock, Panel } from "../components/ui";

const TH = "caption py-3 pr-5 text-left font-medium";

export function System() {
  const { meta, summary, className } = useApp();
  const portfolio = useAsync((signal) => api.portfolio(signal), []);
  const sourceCounts: Record<string, number> = {};
  for (const d of summary.days) for (const [source, n] of Object.entries(d.by_source)) sourceCounts[source] = (sourceCounts[source] ?? 0) + n;
  const first = summary.days[0]?.date;
  const last = summary.days.at(-1)?.date;
  const ruleCount = Object.keys(meta.rules).length;
  const scenarioClasses = Object.keys(meta.scenarios) as EventClass[];

  const steps = [
    { title: "Ingest", body: summary.sources.map((s) => SOURCE_TEXT[s] ?? s).join(" and ") },
    { title: "Clean and dedupe", body: "Strip HTML, links and handles; exact-hash dedup keeps outlet breadth" },
    { title: "Tag entities", body: `${integer(Object.keys(meta.entities).length)} known entities and cashtags set the scope` },
    { title: "Classify", body: `${ruleCount} weighted rules across ${Object.keys(meta.classes).length} event classes` },
    { title: "Score sentiment", body: summary.sentiment_models.join(", ") },
    { title: "Score impact", body: "Item rubric, then cluster severity, breadth and abnormal volume" },
    { title: "Check triggers", body: `${CHECK_ORDER.length} checks including a ${summary.trigger_settings.cooldown_hours}-hour cooldown` },
    { title: "Stress the book", body: "Scope-aware shocks, sensitivity revaluation and exact attribution" },
  ];

  return (
    <div className="grid grid-cols-12 gap-5">
      <Panel className="col-span-12" title="From headline to stress result" description="One Python engine feeds both the Streamlit reference app and this interface">
        <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-8">
          {steps.map((step, index) => (
            <li key={step.title} className="flex min-w-0 flex-col gap-2 rounded-xl bg-surface-2 px-4 py-4">
              <span className="num flex h-[22px] w-[22px] items-center justify-center rounded-full bg-teal text-[11.5px] font-semibold text-on-teal">{index + 1}</span>
              <span className="text-[14px] font-semibold text-ink">{step.title}</span>
              <span className="text-[12.5px] leading-snug text-ink-3">{step.body}</span>
            </li>
          ))}
        </ol>
        <p className="mt-6 max-w-[90ch] text-[13px] leading-relaxed text-ink-3">
          Everything is precomputed by <span className="num text-ink-2">python -m src.pipeline</span> into versioned JSONL files. This interface reads them through a thin read-only API (
          <span className="num text-ink-2">python -m src.api</span>) and never re-implements scoring or valuation.
        </p>
      </Panel>

      <Panel className="col-span-12 md:col-span-6 xl:col-span-4" title="Dataset" description={summary.dataset.label}>
        <dl className="divide-y divide-line">
          <KeyValue label="Window">{first && last ? `${day(first)} to ${day(last)}` : "n/a"}</KeyValue>
          <KeyValue label="Signals" mono>{integer(summary.totals.signals)}</KeyValue>
          {Object.entries(sourceCounts).map(([source, n]) => (
            <KeyValue key={source} label={SOURCE_TEXT[source] ?? source} mono>
              {integer(n)}
            </KeyValue>
          ))}
          <KeyValue label="Event clusters" mono>{integer(summary.totals.events)}</KeyValue>
          <KeyValue label="Stress tests triggered" mono>{integer(summary.totals.triggered)}</KeyValue>
          <KeyValue label="Engine version" mono>{summary.build?.engine_version ?? meta.engine_version}</KeyValue>
          <KeyValue label="Build" mono>{summary.build?.build_id ?? "n/a"}</KeyValue>
          <KeyValue label="Config hash" mono>{summary.build?.config_hash ?? "n/a"}</KeyValue>
          <KeyValue label="Shocks version" mono>{summary.shocks_version}</KeyValue>
        </dl>
      </Panel>

      <Panel className="col-span-12 md:col-span-6 xl:col-span-4" title="Trigger conditions" description="From config/shocks.yaml">
        <dl className="divide-y divide-line">
          <KeyValue label="Stress-relevant classes">{summary.trigger_settings.stress_classes.length} classes</KeyValue>
          <KeyValue label="Event impact" mono>Above {summary.trigger_settings.impact_threshold}</KeyValue>
          <KeyValue label="Mean confidence" mono>At least {summary.trigger_settings.min_confidence}</KeyValue>
          <KeyValue label="Mean sentiment" mono>At most {signed(summary.trigger_settings.max_sentiment)}</KeyValue>
          <KeyValue label="Distinct outlets" mono>At least {summary.trigger_settings.min_news_outlets}</KeyValue>
          <KeyValue label="Cooldown per class" mono>{summary.trigger_settings.cooldown_hours} hours</KeyValue>
          <KeyValue label="Re-arm impact increase" mono>{summary.trigger_settings.rearm_impact_delta}</KeyValue>
          <KeyValue label="Severity floor" mono>×{meta.severity.floor_multiplier}</KeyValue>
          <KeyValue label="Maximum rating notches" mono>{meta.severity.max_rating_notches}</KeyValue>
        </dl>
        <p className="mt-4 text-[12.5px] leading-relaxed text-ink-3">{summary.trigger_settings.stress_classes.map((c) => className(c)).join(", ")}</p>
      </Panel>

      <Panel className="col-span-12 xl:col-span-4" title="Synthetic wholesale book" description="data/portfolio/portfolio_v1.csv">
        {portfolio.error && <ErrorState error={portfolio.error} onRetry={portfolio.reload} compact />}
        {!portfolio.error && !portfolio.data && <LoadingBlock rows={5} />}
        {portfolio.data && (
          <>
            <p className="caption">Market value</p>
            <p className="figure mt-1.5 mb-6 text-[30px] text-ink">{usdMillions(portfolio.data.total_market_value)}</p>
            <HBarList
              rows={portfolio.data.by_asset_class
                .map((row) => ({ key: row.asset_class, label: `${ASSET_TEXT[row.asset_class]} (${row.positions})`, value: Math.abs(row.market_value), emphasis: true }))
                .sort((a, b) => b.value - a.value)}
              formatValue={(v) => usdMillions(v)}
            />
            <p className="mt-5 text-[12.5px] leading-relaxed text-ink-3">
              {portfolio.data.positions.length} positions in {portfolio.data.currency}. Credit obligors are synthetic; only equities and options use real tickers. Swap values are
              shown in absolute terms.
            </p>
          </>
        )}
      </Panel>

      <Panel className="col-span-12" title="Scenario library" description="Base shocks before severity scaling" bodyClassName="px-3 pt-2 pb-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-[13.5px]">
            <caption className="sr-only">Base scenario shocks by event class</caption>
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className={`${TH} pl-3`}>Event class</th>
                <th scope="col" className={`${TH} text-right`}>Equity</th>
                <th scope="col" className={`${TH} text-right`}>Rates</th>
                <th scope="col" className={`${TH} text-right`}>IG / HY spreads</th>
                <th scope="col" className={`${TH} text-right`}>Volatility</th>
                <th scope="col" className={`${TH} pr-3 text-right`}>In-scope add-on</th>
              </tr>
            </thead>
            <tbody>
              {scenarioClasses.map((cls) => {
                const s = meta.scenarios[cls];
                if (!s) return null;
                return (
                  <tr key={cls} className="row-hover border-b border-line last:border-b-0">
                    <th scope="row" className="py-3.5 pr-5 pl-3 text-left font-medium text-ink">{className(cls)}</th>
                    <td className="num py-3.5 pr-5 text-right text-ink-2">{percent(s.equity_market, 0)}</td>
                    <td className="num py-3.5 pr-5 text-right text-ink-2">{basisPoints(s.rates_bp)}</td>
                    <td className="num py-3.5 pr-5 text-right text-ink-2">
                      {signed(s.spread_bp.IG, 0)} / {signed(s.spread_bp.HY, 0)} bp
                    </td>
                    <td className="num py-3.5 pr-5 text-right text-ink-2">{signed(s.vol_pts, 0)} pts</td>
                    <td className="num py-3.5 pr-3 text-right text-ink-2">
                      {basisPoints(s.in_scope.spread_bp)}, {s.in_scope.rating_notches} notch, {percent(s.in_scope.equity_excess, 0)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
