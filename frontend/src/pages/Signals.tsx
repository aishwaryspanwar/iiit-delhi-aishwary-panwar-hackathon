import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Search, SearchX, X } from "lucide-react";
import { useApp } from "../state";
import { api, type SignalQuery } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { integer, shortDay, time } from "../lib/format";
import { SENTIMENT_TEXT, SOURCE_TEXT, impactBand } from "../lib/risk";
import type { Signal } from "../lib/types";
import { MultiSelect } from "../components/MultiSelect";
import { ClassTag, EmptyState, ErrorState, ImpactMeter, SentimentValue, cx } from "../components/ui";
import { SignalRowsSkeleton } from "../components/Skeletons";

const PAGE_SIZE = 50;
const IMPACT_STEPS = [1, 3, 5, 6, 7, 8, 9];

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

const TH = "caption py-3 pr-5 text-left font-normal";

export function Signals() {
  const { dataset, summary, replay, className, openDetail, revision } = useApp();
  const threshold = summary.trigger_settings.impact_threshold;
  const [search, setSearch] = useState("");
  const [classes, setClasses] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [sentiments, setSentiments] = useState<string[]>([]);
  const [minImpact, setMinImpact] = useState(1);
  const [sort, setSort] = useState<"time" | "impact">("time");
  const [followReplay, setFollowReplay] = useState(true);
  const [offset, setOffset] = useState(0);
  const q = useDebounced(search, 280);

  const query: SignalQuery = useMemo(
    () => ({ until: followReplay ? replay.day : undefined, classes, sources, sentiments, minImpact, q, sort, offset, limit: PAGE_SIZE }),
    [followReplay, replay.day, classes, sources, sentiments, minImpact, q, sort, offset],
  );
  useEffect(() => setOffset(0), [followReplay, replay.day, classes, sources, sentiments, minImpact, q, sort, dataset]);

  const page = useAsync((signal) => api.signals(dataset, query, signal), [dataset, JSON.stringify(query), revision]);
  const filtersActive = classes.length + sources.length + sentiments.length > 0 || minImpact > 1 || q.trim().length > 0;
  const reset = () => {
    setSearch("");
    setClasses([]);
    setSources([]);
    setSentiments([]);
    setMinImpact(1);
  };

  const total = page.data?.total ?? 0;
  const from = total ? offset + 1 : 0;
  const to = Math.min(offset + PAGE_SIZE, total);
  const statusText = page.loading && !page.data ? "Loading signals" : `Showing ${integer(from)}–${integer(to)} of ${integer(total)} signals`;

  return (
    <section className="panel" aria-labelledby="feed-title">
      <header className="flex flex-wrap items-center justify-between gap-4 px-6 pt-6">
        <h2 id="feed-title" className="sr-only">
          Scored signals
        </h2>
        <span className="text-[13.5px] text-ink-2" aria-live="polite">
          {statusText}
        </span>
        <div className="flex gap-1.5">
          <button type="button" className="chip" aria-pressed={followReplay} onClick={() => setFollowReplay(true)}>
            Up to replay date
          </button>
          <button type="button" className="chip" aria-pressed={!followReplay} onClick={() => setFollowReplay(false)}>
            Entire window
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2.5 px-6 pt-5 pb-4" role="search">
        <label className="relative flex min-w-[240px] flex-1 items-center">
          <span className="sr-only">Search headlines and outlets</span>
          <Search size={15} className="pointer-events-none absolute left-3.5 text-ink-3" aria-hidden="true" />
          <input type="search" value={search} maxLength={120} onChange={(e) => setSearch(e.target.value)} placeholder="Search headlines, posts or outlets" className="control w-full pl-10" />
        </label>
        <MultiSelect label="Class" options={summary.classes.map((c) => ({ value: c, label: className(c) }))} value={classes} onChange={setClasses} />
        <MultiSelect label="Source" options={summary.sources.map((s) => ({ value: s, label: SOURCE_TEXT[s] ?? s }))} value={sources} onChange={setSources} />
        <MultiSelect label="Sentiment" options={(["neg", "neu", "pos"] as const).map((s) => ({ value: s, label: SENTIMENT_TEXT[s] }))} value={sentiments} onChange={setSentiments} />
        <label className="flex items-center">
          <span className="sr-only">Minimum item impact</span>
          <select className={cx("control", minImpact > 1 && "bg-teal-soft font-semibold text-teal-ink")} value={minImpact} onChange={(e) => setMinImpact(Number(e.target.value))}>
            {IMPACT_STEPS.map((v) => (
              <option key={v} value={v}>
                {v === 1 ? "Any impact" : `Impact ${v} or more`}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center">
          <span className="sr-only">Sort order</span>
          <select className="control" value={sort} onChange={(e) => setSort(e.target.value as "time" | "impact")}>
            <option value="time">Newest first</option>
            <option value="impact">Highest impact first</option>
          </select>
        </label>
        {filtersActive && (
          <button type="button" className="btn btn-ghost text-ink-2" onClick={reset}>
            <X size={14} aria-hidden="true" /> Clear filters
          </button>
        )}
      </div>

      <div className="border-t border-line" />

      {page.error && <ErrorState error={page.error} onRetry={page.reload} />}
      {!page.error && !page.data && (
        <div role="status">
          <span className="sr-only">Loading signals</span>
          <SignalRowsSkeleton />
        </div>
      )}
      {!page.error && page.data && page.data.items.length === 0 && (
        <EmptyState
          title="No matching signals"
          body={followReplay ? "Nothing matches these filters up to the replay date. Widen the filters or move the replay date forward." : "Nothing matches these filters."}
          icon={<SearchX size={18} />}
          action={
            filtersActive ? (
              <button type="button" className="btn mt-3" onClick={reset}>
                Clear filters
              </button>
            ) : undefined
          }
        />
      )}
      {!page.error && page.data && page.data.items.length > 0 && (
        <div className={cx("overflow-x-auto px-3 transition-opacity duration-200", page.loading && "opacity-60")}>
          <table className="w-full min-w-[940px] border-collapse text-[13.5px]">
            <caption className="sr-only">Risk signals with classification, sentiment and impact</caption>
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className={cx(TH, "w-[112px] pl-3")}>Published</th>
                <th scope="col" className={cx(TH, "w-[160px]")}>Source</th>
                <th scope="col" className={TH}>Headline or post</th>
                <th scope="col" className={cx(TH, "w-[160px]")}>Event class</th>
                <th scope="col" className={cx(TH, "w-[120px]")}>Sentiment</th>
                <th scope="col" className={cx(TH, "w-[190px] pr-3")}>Impact</th>
              </tr>
            </thead>
            <tbody>
              {page.data.items.map((signal) => (
                <SignalRow key={signal.signal_id} signal={signal} threshold={threshold} label={className(signal.event.class)} onOpen={() => openDetail({ kind: "signal", id: signal.signal_id })} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {page.data && total > PAGE_SIZE && (
        <nav className="flex items-center justify-between gap-3 border-t border-line px-6 py-4" aria-label="Pagination">
          <span className="num text-[13px] text-ink-3">
            Page {Math.floor(offset / PAGE_SIZE) + 1} of {Math.ceil(total / PAGE_SIZE)}
          </span>
          <div className="flex gap-2">
            <button type="button" className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              <ChevronLeft size={15} aria-hidden="true" /> Previous
            </button>
            <button type="button" className="btn" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next <ChevronRight size={15} aria-hidden="true" />
            </button>
          </div>
        </nav>
      )}
      {page.data && total <= PAGE_SIZE && <div className="h-3" />}
    </section>
  );
}

function SignalRow({ signal, threshold, label, onOpen }: { signal: Signal; threshold: number; label: string; onOpen: () => void }) {
  const band = impactBand(signal.impact.score, threshold);
  const flagged = band === "high" || band === "critical";
  return (
    <tr onClick={onOpen} className="row-hover cursor-pointer border-b border-line last:border-b-0">
      <td className="py-3.5 pr-5 pl-3 align-top whitespace-nowrap">
        <span className="num block text-[13px] text-ink-2">{shortDay(signal.published_at)}</span>
        <span className="num block text-[12px] text-ink-3">{time(signal.published_at)}</span>
      </td>
      <td className="py-3.5 pr-5 align-top">
        <span className="block truncate text-[13px] text-ink-2">{signal.outlet ?? "—"}</span>
        <span className="block text-[12px] text-ink-3">{SOURCE_TEXT[signal.source] ?? signal.source}</span>
      </td>
      <td className="py-3.5 pr-5 align-top">
        <span className="flex items-start gap-2.5">
          {flagged && <span className={cx("mt-[7px] h-2 w-2 shrink-0 rounded-full", band === "critical" ? "bg-critical" : "bg-high")} aria-hidden="true" />}
          <span className="min-w-0">
            <button
              type="button"
              className="line-clamp-2 text-left text-[14px] leading-snug text-ink decoration-ink-3 hover:underline"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              {signal.text}
            </button>
            {signal.duplicate_count > 1 && <span className="num mt-0.5 block text-[12px] text-ink-3">Reported {signal.duplicate_count} times</span>}
          </span>
        </span>
      </td>
      <td className="py-3.5 pr-5 align-top">
        <ClassTag label={label} emphasis={signal.event.class !== "other"} />
      </td>
      <td className="py-3.5 pr-5 align-top">
        <SentimentValue value={signal.sentiment.score} label={signal.sentiment.label} />
      </td>
      <td className="py-3.5 pr-3 align-top">
        <ImpactMeter value={signal.impact.score} threshold={threshold} />
      </td>
    </tr>
  );
}
