import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useApp } from "../state";
import { dateTime, dayWithWeekday, integer, score, shortDay, time } from "../lib/format";
import { STATUS_TEXT } from "../lib/risk";
import type { EventRow, EventStatus } from "../lib/types";
import { ClassTag, StatusIcon } from "./ui";

const DAY_MS = 86_400_000;
const HOUR_MS = 3_600_000;
const FONT = "Google Sans Flex, sans-serif";
const MARGIN = { top: 40, right: 72, bottom: 34, left: 34 };
const ROWS = 10;
const BUCKET_HOURS = [1, 2, 3, 4, 6, 8, 12, 24];
const TOOLTIP_WIDTH = 300;
const STATUS_ORDER: EventStatus[] = ["below", "blocked", "triggered"];

interface Bucket {
  index: number;
  start: number;
  end: number;
  count: number;
  above: number;
  triggered: number;
  peak: EventRow | null;
  focus: EventRow | null;
  status: EventStatus;
}

function pickHours(spanHours: number, plotW: number, rowPitch: number): number {
  return BUCKET_HOURS.find((h) => plotW / Math.ceil(spanHours / h) >= rowPitch * 0.8) ?? 24;
}

function bucketLabel(bucket: Bucket, hours: number): string {
  const startIso = new Date(bucket.start).toISOString();
  if (hours === 24) return dayWithWeekday(startIso.slice(0, 10));
  return `${dateTime(startIso)} to ${time(new Date(bucket.end).toISOString())}`;
}

export function ImpactTimeline({ events, cutoffDay, threshold, height = 340 }: { events: EventRow[]; cutoffDay: string; threshold: number; height?: number }) {
  const { palette, className, openDetail, summary } = useApp();
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(960);
  const [hover, setHover] = useState<number | null>(null);

  useLayoutEffect(() => {
    const el = frame.current;
    if (!el) return;
    const update = () => setWidth(el.clientWidth || 960);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const days = summary.days;
  const start = days.length ? Date.parse(`${days[0].date}T00:00:00Z`) : 0;
  const end = days.length ? Date.parse(`${days[days.length - 1].date}T00:00:00Z`) + DAY_MS : DAY_MS;
  const spanDays = Math.max(1, Math.round((end - start) / DAY_MS));
  const cutoff = Math.min(Date.parse(`${cutoffDay}T00:00:00Z`) + DAY_MS, end);

  const plotW = Math.max(120, width - MARGIN.left - MARGIN.right);
  const plotH = Math.max(100, height - MARGIN.top - MARGIN.bottom);
  const rowPitch = plotH / ROWS;
  const hours = pickHours(spanDays * 24, plotW, rowPitch);
  const step = hours * HOUR_MS;

  const { buckets, counts } = useMemo(() => {
    const total = Math.max(1, Math.ceil((end - start) / step));
    const list: Bucket[] = Array.from({ length: total }, (_, index) => ({
      index,
      start: start + index * step,
      end: Math.min(start + (index + 1) * step, end),
      count: 0,
      above: 0,
      triggered: 0,
      peak: null,
      focus: null,
      status: "below",
    }));
    const tally: Record<EventStatus, number> = { below: 0, blocked: 0, triggered: 0 };
    for (const event of events) {
      const at = Date.parse(event.t_start);
      if (at < start || at >= end || at >= cutoff) continue;
      const bucket = list[Math.floor((at - start) / step)];
      tally[event.status] += 1;
      bucket.count += 1;
      if (event.impact > threshold) bucket.above += 1;
      if (event.status === "triggered") bucket.triggered += 1;
      if (!bucket.peak || event.impact > bucket.peak.impact) bucket.peak = event;
      if (event.status === "triggered" && (!bucket.focus || event.impact > bucket.focus.impact)) bucket.focus = event;
    }
    for (const bucket of list) {
      bucket.focus = bucket.focus ?? bucket.peak;
      if (bucket.triggered) bucket.status = "triggered";
      else if (bucket.peak && (bucket.peak.status === "blocked" || bucket.peak.impact > threshold)) bucket.status = "blocked";
    }
    return { buckets: list, counts: tally };
  }, [events, start, end, step, cutoff, threshold]);

  const colPitch = plotW / buckets.length;
  const radius = Math.max(1.6, Math.min(5, Math.min(colPitch, rowPitch) * 0.27));
  const xOfIndex = (i: number) => MARGIN.left + (i + 0.5) * colPitch;
  const yOfRow = (row: number) => MARGIN.top + (ROWS - row + 0.5) * rowPitch;
  const xOfTime = (t: number) => MARGIN.left + ((t - start) / (end - start)) * plotW;
  const lineY = MARGIN.top + (ROWS - threshold) * rowPitch;
  const cursorX = xOfTime(cutoff);
  const accentDots: Record<EventStatus, string> = { below: palette.ink, blocked: palette.moderate, triggered: palette.critical };

  const dayWidth = plotW / spanDays;
  const labelEvery = [1, 2, 3, 7, 14].find((k) => dayWidth * k >= 62) ?? 14;
  const dayTicks = days.filter((_, i) => i % labelEvery === 0);

  const chipLabel = shortDay(cutoffDay);
  const chipW = chipLabel.length * 7 + 24;
  const chipX = Math.min(Math.max(cursorX - chipW / 2, MARGIN.left - 8), MARGIN.left + plotW + MARGIN.right - chipW - 2);

  const active = hover !== null ? buckets[hover] : null;
  const activeX = active ? xOfIndex(active.index) : 0;
  const tooltipLeft = active ? (activeX < width / 2 ? activeX + 18 : activeX - 18 - TOOLTIP_WIDTH) : 0;

  const open = (bucket: Bucket) => {
    if (bucket.focus) openDetail({ kind: "event", id: bucket.focus.cluster_id });
  };
  const onKey = (event: KeyboardEvent<SVGRectElement>, bucket: Bucket) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open(bucket);
    }
  };
  const visibleTotal = counts.below + counts.blocked + counts.triggered;
  const peakBucket = buckets.reduce<Bucket | null>((best, b) => (b.peak && (!best?.peak || b.peak.impact > best.peak.impact) ? b : best), null);
  const periodWord = hours === 24 ? "day" : `${hours}-hour period`;

  return (
    <figure className="m-0">
      <figcaption className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-ink-2">
        {STATUS_ORDER.map((status) => (
          <span key={status} className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: accentDots[status], opacity: status === "below" ? 0.8 : 1 }} aria-hidden="true" />
            {STATUS_TEXT[status]}
            <span className="num text-ink-3">{integer(counts[status])}</span>
          </span>
        ))}
        <span className="inline-flex items-center gap-2 text-ink-3">
          <span className="inline-block w-5 border-t border-dashed border-ink-3" aria-hidden="true" />
          Trigger threshold {threshold}
        </span>
        <span className="sr-only">
          Dot-matrix chart of the highest event-cluster impact per {periodWord} up to the replay date, one dot per impact level from 1 to 10. {integer(visibleTotal)} clusters so far,{" "}
          {integer(counts.blocked + counts.triggered)} above the threshold of {threshold}, {integer(counts.triggered)} triggered a stress test.
          {peakBucket?.peak ? ` The highest impact so far is ${score(peakBucket.peak.impact)}, on ${bucketLabel(peakBucket, hours)}.` : ""}
        </span>
      </figcaption>

      <div ref={frame} className="relative" style={{ height }} onMouseLeave={() => setHover(null)}>
        <svg width={width} height={height} className="block overflow-visible" role="img" aria-label="Event-cluster impact timeline">
          <text x={0} y={MARGIN.top - 22} fontSize={11} fontFamily={FONT} fill={palette.ink3}>
            Peak impact
          </text>
          {[1, 4, 7, 10].map((v) => (
            <text key={v} x={MARGIN.left - 12} y={yOfRow(v) + 4} textAnchor="end" fontSize={11.5} fontFamily={FONT} fill={palette.ink3}>
              {v}
            </text>
          ))}

          {active && (
            <rect
              x={MARGIN.left + active.index * colPitch + colPitch * 0.08}
              y={MARGIN.top - 4}
              width={colPitch * 0.84}
              height={plotH + 8}
              rx={Math.min(10, colPitch * 0.42)}
              fill={palette.surface2}
            />
          )}

          {buckets.map((b) => {
            const lit = b.peak ? Math.min(ROWS, Math.max(1, Math.ceil(b.peak.impact))) : 0;
            const dim = active !== null && active.index !== b.index;
            const x = xOfIndex(b.index);
            return (
              <g key={b.index} opacity={dim ? 0.45 : 1} style={{ transition: "opacity 160ms ease" }}>
                {Array.from({ length: ROWS }, (_, r) => {
                  const row = r + 1;
                  const on = row <= lit;
                  const over = on && row > threshold;
                  let fill = palette.ink3;
                  let opacity = 0.16;
                  if (on && over) {
                    fill = accentDots[b.status === "below" ? "blocked" : b.status];
                    opacity = 1;
                  } else if (on) {
                    fill = palette.ink;
                    opacity = 0.42 + 0.5 * (row / ROWS);
                  }
                  return <circle key={row} cx={x} cy={yOfRow(row)} r={radius} fill={fill} fillOpacity={opacity} />;
                })}
              </g>
            );
          })}

          <line x1={MARGIN.left} x2={MARGIN.left + plotW} y1={lineY} y2={lineY} stroke={palette.ink3} strokeDasharray="4 5" strokeOpacity={0.75} />
          <text x={MARGIN.left + plotW + 12} y={lineY + 4} fontSize={11.5} fontWeight={600} fontFamily={FONT} fill={palette.ink2}>
            Trigger {threshold}
          </text>

          {dayTicks.map((d) => (
            <text key={d.date} x={xOfTime(Date.parse(`${d.date}T12:00:00Z`))} y={MARGIN.top + plotH + 24} textAnchor="middle" fontSize={11.5} fontFamily={FONT} fill={palette.ink3}>
              {shortDay(d.date)}
            </text>
          ))}

          <g pointerEvents="none">
            <line x1={cursorX} x2={cursorX} y1={MARGIN.top - 10} y2={MARGIN.top + plotH + 4} stroke={palette.accent} strokeWidth={2} strokeLinecap="round" />
            <rect x={chipX} y={MARGIN.top - 36} width={chipW} height={22} rx={11} fill={palette.accent} />
            <text x={chipX + chipW / 2} y={MARGIN.top - 21} textAnchor="middle" fontSize={11.5} fontWeight={600} fontFamily={FONT} fill="#1a0b02">
              {chipLabel}
            </text>
          </g>

          {buckets.map((b) => {
            if (!b.peak) return null;
            const notable = b.status !== "below";
            return (
              <rect
                key={b.index}
                x={MARGIN.left + b.index * colPitch}
                y={MARGIN.top - 6}
                width={colPitch}
                height={plotH + 12}
                fill="transparent"
                className="cursor-pointer outline-none"
                tabIndex={notable ? 0 : undefined}
                role={notable ? "button" : undefined}
                aria-label={notable ? `${bucketLabel(b, hours)}: peak impact ${score(b.peak.impact)}, ${STATUS_TEXT[b.status].toLowerCase()}. Open the event.` : undefined}
                onMouseEnter={() => setHover(b.index)}
                onFocus={() => setHover(b.index)}
                onBlur={() => setHover(null)}
                onClick={() => open(b)}
                onKeyDown={(e) => onKey(e, b)}
              />
            );
          })}
        </svg>

        {active?.peak && (
          <div className="pointer-events-none absolute z-10" style={{ left: Math.max(0, Math.min(tooltipLeft, width - TOOLTIP_WIDTH)), top: MARGIN.top - 6, width: TOOLTIP_WIDTH }}>
            <div className="overlay rounded-2xl px-4 py-3.5 text-[12.5px] leading-relaxed text-ink">
              <div className="num text-[12px] text-ink-3">{bucketLabel(active, hours)}</div>
              <div className="mt-1.5 flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 font-semibold" style={{ color: active.status === "below" ? palette.neutral : accentDots[active.status] }}>
                  <StatusIcon status={active.status} size={11} />
                  <span className="text-ink">{STATUS_TEXT[active.status]}</span>
                </span>
                <span className="figure text-[19px] text-ink">{score(active.peak.impact)}</span>
              </div>
              <div className="num mt-1 text-[12px] text-ink-3">
                {integer(active.count)} {active.count === 1 ? "cluster" : "clusters"}
                {active.above ? `, ${integer(active.above)} above the threshold` : ""}
              </div>
              {active.focus?.lead?.text && <p className="mt-2.5 line-clamp-3 text-ink-2">“{active.focus.lead.text}”</p>}
              {active.focus && (
                <div className="mt-2.5 flex items-center justify-between gap-3">
                  <ClassTag label={className(active.focus.class)} emphasis />
                  <span className="text-[12px] text-ink-3">Click to see why</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </figure>
  );
}
