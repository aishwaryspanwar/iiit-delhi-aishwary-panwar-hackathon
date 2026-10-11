import { ChevronRight, ShieldAlert } from "lucide-react";
import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { integer, usdMillions } from "../lib/format";
import { CHECK_ORDER } from "../lib/risk";
import { navigate } from "../lib/router";
import { AssetPnlChart, FactorWaterfall, HBarList, SeverityCurve } from "../components/charts";
import { TriggerChecks } from "../components/Detail";
import { AssetTable, BeforeAfter, CausalChain, CreditCapital, PositionsTable, RunPicker, ShockTable } from "../components/stress";
import { EmptyState, ErrorState, Panel, Stat } from "../components/ui";
import { StressMainSkeleton } from "../components/Skeletons";

export function Stress({ selected }: { selected: string | null }) {
  const { dataset, summary, meta, openDetail, revision } = useApp();
  const runs = summary.runs;
  const activeId = selected && runs.some((r) => r.cluster_id === selected) ? selected : (runs[0]?.cluster_id ?? null);
  const detail = useAsync(activeId ? (signal) => api.stressRun(dataset, activeId, signal) : null, [dataset, activeId, revision]);
  const current = detail.data && detail.data.run.cluster_id === activeId ? detail.data : null;

  const failureRows = CHECK_ORDER.filter((c) => (summary.decision_failures[c] ?? 0) > 0).map((c) => ({
    key: c,
    label: meta.check_labels[c],
    value: summary.decision_failures[c] ?? 0,
  }));
  const above = summary.days.reduce((sum, d) => sum + d.above_threshold, 0);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-12 gap-5">
        <aside className="col-span-12 flex flex-col gap-5 xl:col-span-3" aria-label="Stress test selection">
          <Panel title="Triggered events" actions={<span className="num text-[13px] text-ink-3">{integer(runs.length)}</span>} bodyClassName="px-3 pt-3 pb-3">
            {runs.length ? (
              <RunPicker runs={runs} selected={activeId} onSelect={(id) => navigate("stress", id)} />
            ) : (
              <EmptyState title="No event met the trigger conditions" body="No stress test ran on this dataset." icon={<ShieldAlert size={18} />} />
            )}
          </Panel>
          <Panel title="Why most events do not trigger">
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
            <p className="mt-5 text-[12.5px] text-ink-3">A cluster can fail more than one check.</p>
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
            <div role="status">
              <span className="sr-only">Loading stress test</span>
              <StressMainSkeleton />
            </div>
          )}
          {current && (
            <>
              <Panel
                title="Causal chain"
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
                  <div className="mt-6">
                    <BeforeAfter totals={current.run.totals} />
                  </div>
                  <p className="mt-6 text-[13px] text-ink-3">
                    Loan losses are the change in IFRS 9 provisions (<span className="num text-ink-2">{usdMillions(current.run.loan_loss_views.ifrs9_provision_change)}</span>).
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
                <Panel className="col-span-12 xl:col-span-6" title="Stress P&L by asset class">
                  <AssetPnlChart rows={current.run.by_asset_class} />
                </Panel>
                <Panel className="col-span-12 xl:col-span-6" title="P&L by risk factor" description="Adds up exactly to the total">
                  <FactorWaterfall byFactor={current.run.by_factor} total={current.run.totals.pnl} />
                </Panel>
              </div>

              <Panel title="Value by asset class">
                <AssetTable detail={current} />
              </Panel>

              <div className="grid grid-cols-12 gap-5">
                <Panel className="col-span-12 2xl:col-span-8" title="Credit losses and capital">
                  <CreditCapital detail={current} />
                </Panel>
                <Panel className="col-span-12 2xl:col-span-4" title="Severity curve" description="Loss if the same event had scored 7 to 10. Dashed line: actual impact.">
                  <SeverityCurve points={current.run.severity_curve} current={current.run.impact} />
                </Panel>
              </div>

              <div className="grid grid-cols-12 gap-5">
                <Panel className="col-span-12 lg:col-span-6" title="Shocks applied" description="Base scenario × severity multiplier">
                  <ShockTable detail={current} />
                </Panel>
                <Panel className="col-span-12 lg:col-span-6" title="Why it fired">
                  <TriggerChecks event={current.event} decision={current.decision} settings={current.trigger_settings} />
                  <details className="group mt-4">
                    <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[13px] font-semibold text-ink-2 hover:text-ink">
                      <ChevronRight size={14} className="transition-transform duration-150 group-open:rotate-90" aria-hidden="true" />
                      Read the engine's full explanation
                    </summary>
                    <p className="mt-3 text-[13px] leading-relaxed text-ink-2">{current.run.explanation}</p>
                  </details>
                </Panel>
              </div>

              <Panel title="Position-level results">
                <PositionsTable positions={current.run.positions} />
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
