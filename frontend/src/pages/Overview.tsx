import { useMemo } from "react";
import { Activity, ArrowRight, ChevronsRight, ShieldAlert } from "lucide-react";
import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { dayWithWeekday, integer, percent, score, shortDay, usdMillions } from "../lib/format";
import { BAND_LABELS, MODERATE_FROM, criticalFrom, impactBand, type RiskBand } from "../lib/risk";
import { href } from "../lib/router";
import type { EventClass, EventRow } from "../lib/types";
import { DailySentiment, HBarList, ImpactTimeline, SentimentSplit } from "../components/charts";
import { BeforeAfter, CausalChain } from "../components/stress";
import { BandBadge, ClassTag, EmptyState, ErrorState, LoadingBlock, Panel, Stat, StatusIcon, TONE_TEXT, cx } from "../components/ui";

const TRAILING_DAYS = 3;

const POSTURE_COPY: Record<RiskBand, string> = {
  low: "No event cluster in the last three days scores above the moderate band.",
  moderate: "News flow is elevated, but nothing is close to the stress-test trigger.",
  high: "At least one event cluster is above the trigger threshold.",
  critical: "A severe event cluster is in the window; scenario shocks would apply near full strength.",
};

const GAUGE_TONE: Record<RiskBand, string> = { low: "text-low", moderate: "text-moderate-mark", high: "text-high", critical: "text-critical" };

function PostureGauge({ value, band }: { value: number; band: RiskBand }) {
  const fraction = Math.max(0, Math.min(1, (value - 1) / 9));
  const circumference = Math.PI * 64;
  return (
    <svg viewBox="0 0 152 88" className={cx("h-[86px] w-[150px] shrink-0", GAUGE_TONE[band])} aria-hidden="true">
      <path d="M12 80 A64 64 0 0 1 140 80" fill="none" stroke="var(--surface-3)" strokeWidth="10" strokeLinecap="round" />
      <path
        d="M12 80 A64 64 0 0 1 140 80"
        fill="none"
        stroke="currentColor"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${circumference * fraction} ${circumference}`}
        style={{ transition: "stroke-dasharray 500ms cubic-bezier(.16,1,.3,1)" }}
      />
      <text x="76" y="76" textAnchor="middle" fontSize="34" fill="var(--ink)" fontFamily="Peace Sans, sans-serif">
        {value.toFixed(1)}
      </text>
    </svg>
  );
}

function SeeAll({ to, label }: { to: string; label: string }) {
  return (
    <a href={to} className="btn btn-ghost h-8 px-3 text-[13px] text-ink-2">
      {label} <ArrowRight size={14} aria-hidden="true" />
    </a>
  );
}

export function Overview() {
  const { summary, events, replay, className, openDetail, dataset, meta } = useApp();
  const threshold = summary.trigger_settings.impact_threshold;
  const visibleDays = summary.days.slice(0, replay.index + 1);

  const totals = useMemo(() => {
    const byClass: Partial<Record<EventClass, number>> = {};
    const bySentiment = { neg: 0, neu: 0, pos: 0 };
    let signals = 0;
    let clusters = 0;
    let above = 0;
    let triggered = 0;
    for (const d of visibleDays) {
      signals += d.signals;
      clusters += d.events;
      above += d.above_threshold;
      triggered += d.triggered;
      bySentiment.neg += d.by_sentiment.neg;
      bySentiment.neu += d.by_sentiment.neu;
      bySentiment.pos += d.by_sentiment.pos;
      for (const [cls, n] of Object.entries(d.by_class)) byClass[cls as EventClass] = (byClass[cls as EventClass] ?? 0) + (n ?? 0);
    }
    const trailing = visibleDays.slice(-TRAILING_DAYS);
    const peak = Math.max(1, ...trailing.map((d) => d.max_event_impact ?? 1));
    const today = visibleDays.at(-1);
    return { byClass, bySentiment, signals, clusters, above, triggered, peak, today };
  }, [visibleDays]);

  const cutoffIso = `${replay.day}T23:59:59Z`;
  const visibleEvents = useMemo(() => events.filter((e) => e.t_start <= cutoffIso), [events, cutoffIso]);
  const latestRun = useMemo(() => [...summary.runs].reverse().find((r) => r.t_start <= cutoffIso) ?? null, [summary.runs, cutoffIso]);
  const notable = useMemo(() => {
    const flagged = visibleEvents.filter((e) => e.status !== "below");
    const pool = flagged.length ? flagged : [...visibleEvents].sort((a, b) => b.impact - a.impact).slice(0, 6);
    return [...pool].sort((a, b) => b.t_start.localeCompare(a.t_start)).slice(0, 6);
  }, [visibleEvents]);

  const runDetail = useAsync(latestRun ? (signal) => api.stressRun(dataset, latestRun.cluster_id, signal) : null, [dataset, latestRun?.cluster_id]);
  const runReady = latestRun && runDetail.data && runDetail.data.run.cluster_id === latestRun.cluster_id ? runDetail.data : null;

  const band = impactBand(totals.peak, threshold);
  const classRows = Object.entries(totals.byClass)
    .map(([cls, n]) => ({ key: cls, label: className(cls), value: n ?? 0, emphasis: summary.trigger_settings.stress_classes.includes(cls as EventClass) }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="grid grid-cols-12 gap-5">
      <section className="panel col-span-12 flex flex-col gap-4 px-6 py-5 md:px-7 xl:col-span-5" aria-labelledby="posture-title">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="posture-title" className="text-[15.5px] font-semibold text-ink">
              Risk posture
            </h2>
            <p className="mt-1 text-[13px] text-ink-3">Peak event impact over the 72 hours to {dayWithWeekday(replay.day)}</p>
          </div>
          <BandBadge band={band} size="md" />
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <PostureGauge value={totals.peak} band={band} />
          <div className="min-w-[200px] flex-1">
            <p className={cx("figure text-[24px]", TONE_TEXT[band])}>{BAND_LABELS[band]} risk</p>
            <p className="mt-1.5 max-w-[40ch] text-[13px] leading-relaxed text-ink-2">{POSTURE_COPY[band]}</p>
            <p className="mt-1.5 text-[12px] text-ink-3">
              Low below {MODERATE_FROM}, high above {threshold}, critical from {criticalFrom(threshold)}
            </p>
          </div>
        </div>
      </section>

      <section className="panel col-span-12 grid grid-cols-2 content-center gap-x-8 gap-y-6 px-6 py-6 lg:grid-cols-4 xl:col-span-7 xl:px-7" aria-label="Key figures">
        {[
          {
            label: "Signals to date",
            value: integer(totals.signals),
            sub: totals.today ? `${integer(totals.today.signals)} on ${shortDay(totals.today.date)}` : undefined,
          },
          { label: "Event clusters", value: integer(totals.clusters), sub: `${integer(totals.above)} above threshold` },
          {
            label: "Stress tests fired",
            value: integer(totals.triggered),
            sub: `of ${integer(summary.totals.triggered)} in the window`,
            tone: totals.triggered ? ("critical" as const) : ("default" as const),
          },
          {
            label: "Latest stress P&L",
            value: latestRun ? usdMillions(latestRun.totals.pnl) : "None yet",
            sub: latestRun ? `${percent(latestRun.totals.pnl_pct)} of the book` : "No stress test yet",
            tone: latestRun ? ("loss" as const) : ("default" as const),
          },
        ].map((item) => (
          <Stat key={item.label} label={item.label} value={item.value} sub={item.sub} tone={item.tone} />
        ))}
      </section>

      <Panel
        className="col-span-12"
        title="Event-cluster impact timeline"
        description="Each mark is a cluster of related news and posts. The orange cursor is the replay date; press play to watch the window unfold."
        actions={<span className="num text-[13px] text-ink-3">{integer(visibleEvents.length)} clusters so far</span>}
      >
        <ImpactTimeline events={events} cutoffDay={replay.day} threshold={threshold} height={300} />
      </Panel>

      <Panel
        className="col-span-12 lg:col-span-7"
        title="Latest high-impact events"
        description="Clusters above the trigger threshold, newest first"
        actions={<SeeAll to={href("signals")} label="Signal feed" />}
        bodyClassName="px-3 pt-2 pb-3"
      >
        {notable.length ? (
          <ul className="flex flex-col">
            {notable.map((event) => (
              <EventLine key={event.cluster_id} event={event} threshold={threshold} label={className(event.class)} onOpen={() => openDetail({ kind: "event", id: event.cluster_id })} />
            ))}
          </ul>
        ) : (
          <EmptyState title="No event clusters yet" body="The replay date is before the first clustered event. Move it forward to see events arrive." icon={<Activity size={18} />} />
        )}
      </Panel>

      <Panel className="col-span-12 lg:col-span-5" title="What the signals are about" description="Signals to date by event class">
        {classRows.length ? (
          <HBarList rows={classRows} emphasisLabel="Can trigger a stress test" mutedLabel="Other classes" />
        ) : (
          <EmptyState title="No signals yet" body="Move the replay date forward to see signals arrive." />
        )}
      </Panel>

      <Panel
        className="col-span-12"
        title={latestRun ? `Latest stress test: ${className(latestRun.class)} event on ${shortDay(latestRun.t_start)}` : "Portfolio stress test"}
        description="From the news event to the change in portfolio value"
      >
        {!latestRun && (
          <EmptyState
            title="No stress test triggered up to this date"
            body={`A stress test fires when a cluster in one of the ${meta.trigger_settings.stress_classes.length} stress-relevant classes exceeds impact ${threshold} with enough confidence, non-positive tone and corroboration. Press play to replay the window.`}
            icon={<ShieldAlert size={18} />}
          />
        )}
        {latestRun && runDetail.error && <ErrorState error={runDetail.error} onRetry={runDetail.reload} compact />}
        {latestRun && !runDetail.error && !runReady && <LoadingBlock rows={3} />}
        {runReady && (
          <div className="flex flex-col gap-8">
            <CausalChain detail={runReady} />
            <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
              <BeforeAfter totals={runReady.run.totals} size="sm" />
              <a
                href={href("stress", runReady.run.cluster_id)}
                className="group flex items-center justify-between gap-6 rounded-full bg-pill py-2 pr-2 pl-6 text-on-pill shadow-hover transition-transform duration-200 hover:-translate-y-0.5"
              >
                <span className="min-w-0">
                  <span className="block text-[12px] opacity-70">Open the full stress test</span>
                  <span className="block truncate text-[14px] font-semibold">{integer(runReady.run.positions.length)} positions revalued</span>
                </span>
                <span className="figure flex shrink-0 items-center gap-2 rounded-full bg-accent px-5 py-3 text-[17px] text-on-accent shadow-[0_10px_24px_-10px_var(--accent-glow)]">
                  {usdMillions(runReady.run.totals.pnl)}
                  <ChevronsRight size={18} className="transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </a>
            </div>
          </div>
        )}
      </Panel>

      <Panel className="col-span-12" title="Market mood" description={`Sentiment of signals to date, scored with ${summary.sentiment_models.join(", ")}`}>
        <div className="grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <SentimentSplit counts={totals.bySentiment} />
          <div>
            <p className="caption mb-2">Daily mean sentiment</p>
            <DailySentiment days={summary.days} cutoffIndex={replay.index} height={180} />
          </div>
        </div>
      </Panel>
    </div>
  );
}

const STATUS_TONE = { triggered: "text-critical", blocked: "text-moderate-mark", below: "text-neutral" } as const;

function EventLine({ event, threshold, label, onOpen }: { event: EventRow; threshold: number; label: string; onOpen: () => void }) {
  return (
    <li>
      <button type="button" onClick={onOpen} className="flex w-full items-start gap-4 rounded-xl px-3 py-3.5 text-left transition-colors duration-150 hover:bg-surface-2">
        <span className={cx("mt-1 shrink-0", STATUS_TONE[event.status])}>
          <StatusIcon status={event.status} size={12} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 text-[14px] font-medium text-ink md:line-clamp-1">{event.lead?.text ?? event.cluster_id}</span>
          <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-ink-3">
            <span className="num">{shortDay(event.t_start)}</span>
            <ClassTag label={label} />
            <span>
              {event.n_items} items from {event.n_outlets} outlets
            </span>
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1.5">
          <span className="figure text-[17px] text-ink">{score(event.impact)}</span>
          <BandBadge band={impactBand(event.impact, threshold)} />
        </span>
      </button>
    </li>
  );
}
