import { useMemo, useState } from "react";
import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { day, integer, score, signed } from "../lib/format";
import { navigate } from "../lib/router";
import { EmptyState, ErrorState, LoadingBlock, Panel, SentimentValue, StatusBadge, cx } from "../components/ui";

const TYPE_TEXT: Record<string, string> = { company: "Company", country: "Country", sector: "Sector", commodity: "Commodity", central_bank: "Central bank", index: "Index" };
const TH = "caption py-2.5 pr-4 text-left font-medium";

export function Entities({ selected }: { selected: string | null }) {
  const { dataset, className, openDetail } = useApp();
  const [query, setQuery] = useState("");
  const list = useAsync((signal) => api.entities(dataset, signal), [dataset]);
  const activeId = selected ?? list.data?.[0]?.id ?? null;
  const detail = useAsync(activeId ? (signal) => api.entity(dataset, activeId, signal) : null, [dataset, activeId]);
  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (list.data ?? []).filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.id.toLowerCase().includes(needle)).slice(0, 80);
  }, [list.data, query]);
  if (list.error) return <ErrorState error={list.error} onRetry={list.reload} />;
  if (!list.data) return <LoadingBlock rows={6} label="Loading entities" />;
  const current = detail.data && detail.data.entity.id === activeId ? detail.data : null;
  const maxSignals = Math.max(...(current?.timeline.map((d) => d.signals) ?? [1]), 1);
  return (
    <div className="grid grid-cols-12 gap-5">
      <aside className="col-span-12 xl:col-span-4" aria-label="Entity list">
        <Panel title="Companies, countries and sectors" description={`${integer(list.data.length)} entities mentioned in this window`} bodyClassName="px-3 pt-3 pb-3">
          <label className="mb-3 block px-2">
            <span className="sr-only">Search entities</span>
            <input className="control w-full" placeholder="Search by name" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <ul className="flex max-h-[640px] flex-col gap-1 overflow-auto">
            {rows.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  aria-pressed={row.id === activeId}
                  onClick={() => navigate("entities", row.id)}
                  className={cx("w-full rounded-xl px-3 py-2.5 text-left transition-colors", row.id === activeId ? "bg-surface-3 ring-1 ring-accent/70" : "hover:bg-surface-2")}
                >
                  <div className="flex items-center justify-between gap-3 text-[13.5px]">
                    <span className="truncate font-medium text-ink">{row.name}</span>
                    <span className="num shrink-0 text-ink-3">{integer(row.signals)}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-[12px] text-ink-3">
                    <span>{TYPE_TEXT[row.type ?? ""] ?? row.type}</span>
                    <span className="num">sentiment {signed(row.mean_sentiment)}</span>
                    <span className="num">max impact {score(row.max_impact)}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </aside>
      <div className="col-span-12 flex min-w-0 flex-col gap-5 xl:col-span-8">
        {detail.error && <ErrorState error={detail.error} onRetry={detail.reload} />}
        {!detail.error && !current && <LoadingBlock rows={6} label="Loading entity" />}
        {current && (
          <>
            <Panel
              title={current.entity.name}
              description={[TYPE_TEXT[current.entity.type ?? ""] ?? current.entity.type, current.entity.ticker, current.entity.sector, current.entity.country].filter(Boolean).join(" · ")}
            >
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] border-collapse text-[13px]">
                  <caption className="sr-only">Daily signals, sentiment and maximum impact for this entity</caption>
                  <thead>
                    <tr className="border-b border-line">
                      <th scope="col" className={TH}>Day</th>
                      <th scope="col" className={TH}>Signals</th>
                      <th scope="col" className={cx(TH, "text-right")}>Mean sentiment</th>
                      <th scope="col" className={cx(TH, "text-right")}>Max impact</th>
                      <th scope="col" className={TH}>Main class</th>
                    </tr>
                  </thead>
                  <tbody>
                    {current.timeline.map((d) => {
                      const main = Object.entries(d.by_class).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))[0];
                      return (
                        <tr key={d.date} className="border-b border-line last:border-b-0">
                          <th scope="row" className="num py-2 pr-4 text-left font-normal text-ink-2">{day(d.date)}</th>
                          <td className="py-2 pr-4">
                            <div className="flex items-center gap-2">
                              <div className="h-[5px] w-24 rounded-full bg-surface-3" aria-hidden="true">
                                <div className="h-full rounded-full bg-teal" style={{ width: `${(d.signals / maxSignals) * 100}%` }} />
                              </div>
                              <span className="num text-ink-2">{d.signals}</span>
                            </div>
                          </td>
                          <td className="py-2 pr-4 text-right">
                            <SentimentValue value={d.mean_sentiment} />
                          </td>
                          <td className="num py-2 pr-4 text-right text-ink">{score(d.max_impact)}</td>
                          <td className="py-2 pr-4 text-ink-2">{main ? className(main[0]) : "n/a"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Panel>
            <Panel title="Event clusters targeting this entity" description="Highest impact first">
              {current.events.length ? (
                <ul className="flex flex-col divide-y divide-line">
                  {current.events.map((event) => (
                    <li key={event.cluster_id}>
                      <button type="button" className="row-hover flex w-full items-center justify-between gap-4 py-3 text-left" onClick={() => openDetail({ kind: "event", id: event.cluster_id })}>
                        <span className="min-w-0">
                          <span className="block truncate text-[13.5px] font-medium text-ink">{event.lead?.text ?? event.cluster_id}</span>
                          <span className="num text-[12px] text-ink-3">
                            {day(event.t_start)} · {className(event.class)} · {integer(event.n_items)} items
                          </span>
                        </span>
                        <span className="flex shrink-0 items-center gap-3">
                          <span className="num text-[13.5px] font-semibold text-ink">{score(event.impact)}</span>
                          <StatusBadge status={event.status} />
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No clusters are scoped to this entity" body="It is mentioned, but never as the primary target of an event cluster." />
              )}
            </Panel>
          </>
        )}
      </div>
    </div>
  );
}
