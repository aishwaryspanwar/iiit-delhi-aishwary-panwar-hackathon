import { Info, ShieldAlert } from "lucide-react";
import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { integer, usdMillions } from "../lib/format";
import { CHECK_ORDER, DISCLAIMER } from "../lib/risk";
import { navigate } from "../lib/router";
import { AssetPnlChart, FactorWaterfall, HBarList } from "../components/charts";
import { TriggerChecks } from "../components/Detail";
import { AssetTable, BeforeAfter, CausalChain, PositionsTable, RunPicker, ShockTable } from "../components/stress";
import { EmptyState, ErrorState, LoadingBlock, Panel, Stat } from "../components/ui";

export function Stress({ selected }: { selected: string | null }) {
  const { dataset, summary, meta, openDetail } = useApp();
  const runs = summary.runs;
  const activeId = selected && runs.some((r) => r.cluster_id === selected) ? selected : (runs[0]?.cluster_id ?? null);
  const detail = useAsync(activeId ? (signal) => api.stressRun(dataset, activeId, signal) : null, [dataset, activeId]);
  const current = detail.data && detail.data.run.cluster_id === activeId ? detail.data : null;

  const failureRows = CHECK_ORDER.filter((c) => (summary.decision_failures[c] ?? 0) > 0).map((c) => ({
    key: c,
    label: meta.check_labels[c],
    value: summary.decision_failures[c] ?? 0,
  }));
  const above = summary.days.reduce((sum, d) => sum + d.above_threshold, 0);

  return (
    <div className="flex flex-col gap-5">
      <p className="flex items-start gap-2.5 px-1 text-[13px] text-ink-3" role="note">
        <Info size={15} className="mt-0.5 shrink-0 text-moderate" aria-hidden="true" />
        {DISCLAIMER}
      </p>

      <div className="grid grid-cols-12 gap-5">
        <aside className="col-span-12 flex flex-col gap-5 xl:col-span-3" aria-label="Stress test selection">
          <Panel title="Triggered events" description={`${integer(runs.length)} stress tests in this window`} bodyClassName="px-3 pt-3 pb-3">
            {runs.length ? (
              <RunPicker runs={runs} selected={activeId} onSelect={(id) => navigate("stress", id)} />
            ) : (
              <EmptyState title="No event met the trigger conditions" body="No stress test ran on this dataset." icon={<ShieldAlert size={18} />} />
            )}
          </Panel>
          <Panel title="Why most events do not trigger" description="Every cluster passes through the same checks">
            <dl className="mb-6 grid grid-cols-3 gap-3">
              <div>
                <dt className="caption">Clusters</dt>
                <dd className="figure mt-1.5 text-[20px] text-ink">{integer(summary.totals.events)}</dd>
              </div>
              <div>
                <dt className="caption">Above {summary.trigger_settings.impact_threshold}</dt>
                <dd className="figure mt-1.5 text-[20px] text-moderate">{integer(above)}</dd>
              </div>
              <div>
                <dt className="caption">Fired</dt>
                <dd className="figure mt-1.5 text-[20px] text-critical">{integer(summary.totals.triggered)}</dd>
              </div>
            </dl>
            <p className="mb-3 text-[13px] font-semibold text-ink">Checks failed by clusters that did not fire</p>
            <HBarList rows={failureRows} />
            <p className="mt-5 text-[12.5px] leading-relaxed text-ink-3">
              A cluster can fail several checks. The cooldown stops the same class from firing again within {summary.trigger_settings.cooldown_hours} hours.
            </p>
          </Panel>
        </aside>

        <div className="col-span-12 flex min-w-0 flex-col gap-5 xl:col-span-9">
          {!activeId && (
            <Panel title="Stress test">
              <EmptyState title="No stress test triggered" body="Choose another dataset, or score your own headline to preview a scenario." />
            </Panel>
          )}
          {activeId && detail.error && (
            <Panel title="Stress test">
              <ErrorState error={detail.error} onRetry={detail.reload} />
            </Panel>
          )}
          {activeId && !detail.error && !current && (
            <Panel title="Loading stress test">
              <LoadingBlock rows={6} label="Loading stress test" />
            </Panel>
          )}
          {current && (
            <>
              <Panel
                title="Causal chain"
                description="How a news event becomes a change in portfolio value"
                actions={
                  <button type="button" className="btn" onClick={() => openDetail({ kind: "event", id: current.run.cluster_id })}>
                    Explain the event
                  </button>
                }
              >
                <CausalChain detail={current} />
              </Panel>

              <section className="panel grid grid-cols-12" aria-labelledby="value-title">
                <div className="col-span-12 px-7 py-6 lg:col-span-8">
                  <h2 id="value-title" className="text-[15.5px] font-semibold text-ink">
                    Portfolio value before and after stress
                  </h2>
                  <p className="mt-1 mb-6 text-[13px] text-ink-3">USD, synthetic wholesale book</p>
                  <BeforeAfter totals={current.run.totals} />
                  <p className="mt-6 max-w-[72ch] text-[13px] leading-relaxed text-ink-3">
                    Loans are held at amortised cost, so their P&L is the change in one-year expected loss from rating migration (
                    <span className="num text-ink-2">{usdMillions(current.run.loan_loss_views.one_year_el_change)}</span>). On a lifetime view (IFRS 9 stage-2 style
                    sensitivity) the same downgrades cost <span className="num text-ink-2">{usdMillions(current.run.loan_loss_views.lifetime_el_change)}</span>.
                  </p>
                </div>
                <div className="col-span-12 grid grid-cols-2 border-t border-line lg:col-span-4 lg:grid-cols-1 lg:border-t-0 lg:border-l">
                  <div className="px-7 py-6">
                    <Stat label="In-scope positions" value={integer(current.run.in_scope_positions)} sub={`of ${current.run.positions.length}, ${current.summary.scope_label}`} />
                  </div>
                  <div className="border-l border-line px-7 py-6 lg:border-t lg:border-l-0">
                    <Stat
                      label="Severity multiplier"
                      value={`×${current.run.shocks_applied.multiplier.toFixed(2)}`}
                      sub={`Impact ${current.run.impact.toFixed(1)}, scaled from a floor of ${meta.severity.floor_multiplier}`}
                      tone="accent"
                    />
                  </div>
                </div>
              </section>

              <div className="grid grid-cols-12 gap-5">
                <Panel className="col-span-12 2xl:col-span-6" title="Stress P&L by asset class" description="USD millions">
                  <AssetPnlChart rows={current.run.by_asset_class} />
                </Panel>
                <Panel className="col-span-12 2xl:col-span-6" title="P&L by risk factor" description="USD millions, summing exactly to the total">
                  <FactorWaterfall byFactor={current.run.by_factor} total={current.run.totals.pnl} />
                </Panel>
              </div>

              <Panel title="Value by asset class" description="Before and after the stress">
                <AssetTable detail={current} />
              </Panel>

              <div className="grid grid-cols-12 gap-5">
                <Panel className="col-span-12 lg:col-span-6" title="Shocks applied" description="Base scenario scaled by the severity multiplier">
                  <ShockTable detail={current} />
                </Panel>
                <Panel className="col-span-12 lg:col-span-6" title="Why it fired" description="Trigger checks against their thresholds">
                  <TriggerChecks event={current.event} decision={current.decision} settings={current.trigger_settings} />
                  <h3 className="mt-6 mb-2 text-[13.5px] font-semibold text-ink">Engine explanation</h3>
                  <p className="text-[13px] leading-relaxed text-ink-2">{current.run.explanation}</p>
                </Panel>
              </div>

              <Panel title="Position-level results" description="Every position revalued under the applied shocks">
                <PositionsTable positions={current.run.positions} />
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
