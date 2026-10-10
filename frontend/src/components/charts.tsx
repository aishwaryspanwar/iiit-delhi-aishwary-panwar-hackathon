import { useMemo, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { useApp } from "../state";
import { dateTime, integer, score, shortDay, signed, usdMillions, percent } from "../lib/format";
import { ASSET_TEXT, FACTOR_ORDER, FACTOR_TEXT, STATUS_TEXT } from "../lib/risk";
import type { AssetBreakdown, DaySummary, EventRow, EventStatus, Factor } from "../lib/types";
import type { ChartPalette } from "../lib/theme";
import { StatusIcon, cx } from "./ui";

const FONT = "Risk Signs, Open Sauce Sans, sans-serif";
const DAY_MS = 86_400_000;

function tick(palette: ChartPalette, size = 11.5) {
  return { fontSize: size, fontFamily: FONT, fill: palette.ink3 };
}

function TooltipCard({ children }: { children: ReactNode }) {
  return <div className="overlay max-w-[320px] rounded-xl px-4 py-3 text-[12.5px] leading-relaxed text-ink">{children}</div>;
}

const STATUS_ORDER: EventStatus[] = ["below", "blocked", "triggered"];
const STATUS_SHAPE: Record<EventStatus, "circle" | "triangle" | "diamond"> = { below: "circle", blocked: "triangle", triggered: "diamond" };
const FACTOR_SHORT: Record<Factor, string> = { rates: "Rates", spread: "Spread", migration: "Migration", equity: "Equity", vol: "Vol", second_order: "Convexity" };

interface TimelinePoint {
  x: number;
  y: number;
  z: number;
  event: EventRow;
}

function ReplayCursor({ viewBox, palette, label, position }: { viewBox?: { x?: number; y?: number; height?: number }; palette: ChartPalette; label: string; position: number }) {
  const x = viewBox?.x ?? 0;
  const y = viewBox?.y ?? 0;
  const h = viewBox?.height ?? 0;
  const chipWidth = label.length * 7 + 22;
  let chipX = x - chipWidth / 2;
  if (position > 0.9) chipX = x - chipWidth + 4;
  else if (position < 0.1) chipX = x - 4;
  return (
    <g pointerEvents="none">
      <defs>
        <radialGradient id="replay-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={palette.accent} stopOpacity={0.26} />
          <stop offset="100%" stopColor={palette.accent} stopOpacity={0} />
        </radialGradient>
      </defs>
      <ellipse cx={position > 0.9 ? x - 40 : x} cy={y + h * 0.45} rx={70} ry={h * 0.55} fill="url(#replay-glow)" />
      <rect x={chipX} y={y - 27} width={chipWidth} height={22} rx={11} fill={palette.accent} />
      <text x={chipX + chipWidth / 2} y={y - 12} textAnchor="middle" fontSize={11.5} fontWeight={600} fontFamily={FONT} fill="#1a0b02">
        {label}
      </text>
    </g>
  );
}

export function ImpactTimeline({ events, cutoffDay, threshold, height = 340 }: { events: EventRow[]; cutoffDay: string; threshold: number; height?: number }) {
  const { palette, className, openDetail, summary } = useApp();
  const domain = useMemo(() => {
    const days = summary.days;
    if (!days.length) return [0, 1];
    return [Date.parse(`${days[0].date}T00:00:00Z`), Date.parse(`${days[days.length - 1].date}T00:00:00Z`) + DAY_MS];
  }, [summary.days]);
  const cutoff = Math.min(Date.parse(`${cutoffDay}T00:00:00Z`) + DAY_MS, domain[1]);
  const series = useMemo(() => {
    const grouped: Record<EventStatus, TimelinePoint[]> = { below: [], blocked: [], triggered: [] };
    for (const event of events) {
      const x = Date.parse(event.t_start);
      if (x >= cutoff) continue;
      grouped[event.status].push({ x, y: event.impact, z: event.status === "below" ? Math.min(event.n_items, 40) : 40, event });
    }
    return grouped;
  }, [events, cutoff]);
  const colors: Record<EventStatus, string> = { below: palette.neutral, blocked: palette.moderate, triggered: palette.critical };
  const ticks = useMemo(() => {
    const result: number[] = [];
    const span = domain[1] - domain[0];
    let stepDays = 1;
    if (span > 30 * DAY_MS) stepDays = 7;
    else if (span > 10 * DAY_MS) stepDays = 3;
    for (let t = domain[0]; t <= domain[1]; t += stepDays * DAY_MS) result.push(t);
    return result;
  }, [domain]);

  return (
    <figure className="m-0">
      <figcaption className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-ink-2">
        {STATUS_ORDER.map((status) => (
          <span key={status} className="inline-flex items-center gap-2">
            <span style={{ color: colors[status] }}>
              <StatusIcon status={status} size={11} />
            </span>
            {STATUS_TEXT[status]}
            <span className="num text-ink-3">{integer(series[status].length)}</span>
          </span>
        ))}
        <span className="inline-flex items-center gap-2 text-ink-3">
          <span className="inline-block w-5 border-t border-dashed border-ink-3" aria-hidden="true" />
          Trigger threshold {threshold}
        </span>
        <span className="sr-only">Scatter plot of event-cluster impact over time up to the replay date. Points above the dashed threshold line may trigger a stress test.</span>
      </figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 32, right: 16, bottom: 4, left: -14 }}>
            <CartesianGrid stroke={palette.grid} vertical={false} />
            <XAxis
              type="number"
              dataKey="x"
              domain={domain}
              ticks={ticks}
              tickFormatter={(value: number) => shortDay(new Date(value).toISOString())}
              tick={tick(palette)}
              axisLine={false}
              tickLine={false}
              tickMargin={10}
              scale="time"
            />
            <YAxis type="number" dataKey="y" domain={[1, 10]} ticks={[1, 4, 7, 10]} tick={tick(palette)} axisLine={false} tickLine={false} tickMargin={6} />
            <ZAxis type="number" dataKey="z" range={[10, 90]} domain={[1, 40]} />
            {cutoff < domain[1] && <ReferenceArea x1={cutoff} x2={domain[1]} fill={palette.surface2} fillOpacity={0.6} strokeOpacity={0} ifOverflow="hidden" />}
            <ReferenceLine y={threshold} stroke={palette.ink3} strokeDasharray="5 5" strokeOpacity={0.7} />
            <ReferenceLine
              x={cutoff}
              stroke={palette.accent}
              strokeWidth={1.5}
              label={(props: { viewBox?: { x?: number; y?: number; height?: number } }) => <ReplayCursor viewBox={props.viewBox} palette={palette} label={shortDay(cutoffDay)} position={(cutoff - domain[0]) / (domain[1] - domain[0])} />}
            />
            <Tooltip
              cursor={{ stroke: palette.ink3, strokeDasharray: "3 4", strokeWidth: 1 }}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const point = active && payload?.length ? (payload[0].payload as TimelinePoint) : null;
                if (!point) return null;
                const e = point.event;
                return (
                  <TooltipCard>
                    <div className="mb-1 flex items-center gap-2 font-semibold">
                      <span style={{ color: colors[e.status] }}>
                        <StatusIcon status={e.status} size={10} />
                      </span>
                      {className(e.class)}, impact <span className="num">{score(e.impact)}</span>
                    </div>
                    {e.lead?.text && <p className="mb-2 line-clamp-3 text-ink-2">“{e.lead.text}”</p>}
                    <div className="num text-[12px] text-ink-3">{dateTime(e.t_start)}</div>
                    <div className="text-[12px] text-ink-3">
                      {e.n_items} items from {e.n_outlets} outlets. {STATUS_TEXT[e.status]}.
                    </div>
                  </TooltipCard>
                );
              }}
            />
            {STATUS_ORDER.map((status) => (
              <Scatter
                key={status}
                data={series[status]}
                fill={colors[status]}
                fillOpacity={status === "below" ? 0.3 : 1}
                stroke={status === "below" ? "none" : palette.surface}
                strokeWidth={2}
                shape={STATUS_SHAPE[status]}
                isAnimationActive={false}
                cursor="pointer"
                onClick={(item: unknown) => {
                  const point = (item as { payload?: TimelinePoint }).payload;
                  if (point) openDetail({ kind: "event", id: point.event.cluster_id });
                }}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export function DailySentiment({ days, cutoffIndex, height = 200 }: { days: DaySummary[]; cutoffIndex: number; height?: number }) {
  const { palette } = useApp();
  const data = days.map((d, i) => ({ date: d.date, mean: d.signals ? d.sentiment_sum / d.signals : 0, visible: i <= cutoffIndex, signals: d.signals }));
  return (
    <figure className="m-0">
      <figcaption className="sr-only">Daily mean sentiment of all signals, one column per day; columns below zero are net negative.</figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barCategoryGap="18%">
            <CartesianGrid stroke={palette.grid} vertical={false} />
            <XAxis dataKey="date" tickFormatter={(v: string) => shortDay(v)} tick={tick(palette)} axisLine={false} tickLine={false} minTickGap={28} tickMargin={10} />
            <YAxis tick={tick(palette)} axisLine={false} tickLine={false} tickFormatter={(v: number) => signed(v)} width={48} />
            <ReferenceLine y={0} stroke={palette.axis} />
            <Tooltip
              cursor={{ fill: palette.grid }}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const row = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null;
                if (!row) return null;
                return (
                  <TooltipCard>
                    <div className="font-semibold">{shortDay(row.date)}</div>
                    <div className="num text-ink-2">Mean sentiment {signed(row.mean)}</div>
                    <div className="num text-ink-3">{integer(row.signals)} signals</div>
                  </TooltipCard>
                );
              }}
            />
            <Bar dataKey="mean" maxBarSize={10} minPointSize={2} radius={2} isAnimationActive={false}>
              {data.map((row) => {
                let fill = palette.surface2;
                if (row.visible) fill = row.mean < 0 ? palette.loss : palette.gain;
                return <Cell key={row.date} fill={fill} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

function ValueLabel({ x, y, text, anchor, palette }: { x: number; y: number; text: string; anchor: "start" | "middle"; palette: ChartPalette }) {
  return (
    <text x={x} y={y} textAnchor={anchor} fontSize={12} fontWeight={500} fontFamily={FONT} fill={palette.ink2}>
      {text}
    </text>
  );
}

function millionsLabel(v: number): string {
  return `${v < 0 ? "−" : "+"}${Math.abs(v).toFixed(1)}m`;
}

export function AssetPnlChart({ rows, height = 250 }: { rows: AssetBreakdown[]; height?: number }) {
  const { palette } = useApp();
  const data = [...rows]
    .sort((a, b) => a.pnl - b.pnl)
    .map((row) => ({ label: ASSET_TEXT[row.asset_class], pnl: row.pnl / 1e6, raw: row, pct: row.value_before ? row.pnl / Math.abs(row.value_before) : 0 }));
  return (
    <figure className="m-0">
      <figcaption className="sr-only">Stress profit and loss by asset class in USD millions. Negative values are losses.</figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 64, bottom: 4, left: 4 }} barCategoryGap={10}>
            <CartesianGrid stroke={palette.grid} horizontal={false} />
            <XAxis type="number" tick={tick(palette)} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}m`} />
            <YAxis type="category" dataKey="label" width={138} tick={{ fontSize: 13, fontFamily: FONT, fill: palette.ink2 }} axisLine={false} tickLine={false} />
            <ReferenceLine x={0} stroke={palette.axis} />
            <Tooltip
              cursor={{ fill: palette.grid }}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const row = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null;
                if (!row) return null;
                return (
                  <TooltipCard>
                    <div className="font-semibold">{row.label}</div>
                    <div className="num text-ink-2">
                      {usdMillions(row.raw.value_before)} before, {usdMillions(row.raw.value_after)} after
                    </div>
                    <div className="num">
                      P&L {usdMillions(row.raw.pnl, 2, true)} ({percent(row.pct)})
                    </div>
                  </TooltipCard>
                );
              }}
            />
            <Bar dataKey="pnl" maxBarSize={18} radius={6} isAnimationActive={false}>
              {data.map((row) => (
                <Cell key={row.label} fill={row.pnl < 0 ? palette.loss : palette.gain} />
              ))}
              <LabelList
                dataKey="pnl"
                content={(props) => {
                  const { x = 0, y = 0, width = 0, height: h = 0, value } = props as { x?: number; y?: number; width?: number; height?: number; value?: number };
                  const end = Number(x) + Math.max(Number(width), 0);
                  return <ValueLabel x={end + 8} y={Number(y) + Number(h) / 2 + 4} text={millionsLabel(Number(value ?? 0))} anchor="start" palette={palette} />;
                }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export function FactorWaterfall({ byFactor, total, height = 260 }: { byFactor: Record<Factor, number>; total: number; height?: number }) {
  const { palette } = useApp();
  const data = useMemo(() => {
    let running = 0;
    const rows = FACTOR_ORDER.filter((f) => f in byFactor).map((factor) => {
      const value = byFactor[factor] / 1e6;
      const start = running;
      running += value;
      return { label: FACTOR_SHORT[factor], full: FACTOR_TEXT[factor], range: [start, running] as [number, number], value, kind: value < 0 ? "loss" : "gain" };
    });
    rows.push({ label: "Total", full: "Total stress P&L", range: [0, total / 1e6], value: total / 1e6, kind: "total" });
    return rows;
  }, [byFactor, total]);
  const fills: Record<string, string> = { loss: palette.loss, gain: palette.gain, total: palette.ink2 };
  return (
    <figure className="m-0">
      <figcaption className="sr-only">Waterfall of stress P&L attribution by risk factor, ending in the total P&L.</figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 22, right: 8, bottom: 4, left: -6 }} barCategoryGap="26%">
            <CartesianGrid stroke={palette.grid} vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fontFamily: FONT, fill: palette.ink2 }} axisLine={false} tickLine={false} interval={0} tickMargin={10} />
            <YAxis tick={tick(palette)} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}m`} />
            <ReferenceLine y={0} stroke={palette.axis} />
            <Tooltip
              cursor={{ fill: palette.grid }}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const row = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null;
                if (!row) return null;
                return (
                  <TooltipCard>
                    <div className="font-semibold">{row.full}</div>
                    <div className="num text-ink-2">{usdMillions(row.value * 1e6, 2, true)}</div>
                  </TooltipCard>
                );
              }}
            />
            <Bar dataKey="range" maxBarSize={34} radius={6} isAnimationActive={false}>
              {data.map((row) => (
                <Cell key={row.label} fill={fills[row.kind]} />
              ))}
              <LabelList
                dataKey="value"
                content={(props) => {
                  const { x = 0, y = 0, width = 0, height: h = 0, value } = props as { x?: number; y?: number; width?: number; height?: number; value?: number };
                  const top = Math.min(Number(y), Number(y) + Number(h));
                  return <ValueLabel x={Number(x) + Number(width) / 2} y={top - 8} text={millionsLabel(Number(value ?? 0))} anchor="middle" palette={palette} />;
                }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export function HBarList({
  rows,
  formatValue = integer,
  emphasisLabel,
  mutedLabel,
}: {
  rows: { key: string; label: string; value: number; emphasis?: boolean }[];
  formatValue?: (value: number) => string;
  emphasisLabel?: string;
  mutedLabel?: string;
}) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <div>
      {(emphasisLabel || mutedLabel) && (
        <div className="mb-4 flex flex-wrap gap-x-5 gap-y-1 text-[12.5px] text-ink-3">
          {emphasisLabel && (
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-teal" aria-hidden="true" />
              {emphasisLabel}
            </span>
          )}
          {mutedLabel && (
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-neutral/60" aria-hidden="true" />
              {mutedLabel}
            </span>
          )}
        </div>
      )}
      <ul className="flex flex-col gap-3.5">
        {rows.map((row) => (
          <li key={row.key}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3 text-[13.5px]">
              <span className="line-clamp-2 min-w-0 text-ink-2">{row.label}</span>
              <span className="num shrink-0 font-medium text-ink">{formatValue(row.value)}</span>
            </div>
            <div className="h-[5px] rounded-full bg-surface-3" aria-hidden="true">
              <div
                className={cx("h-full rounded-full transition-[width] duration-500 ease-out", row.emphasis ? "bg-teal" : "bg-neutral/60")}
                style={{ width: `${(row.value / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SentimentSplit({ counts }: { counts: { neg: number; neu: number; pos: number } }) {
  const total = counts.neg + counts.neu + counts.pos || 1;
  const parts = [
    { key: "neg", label: "Negative", value: counts.neg, className: "bg-loss" },
    { key: "neu", label: "Neutral", value: counts.neu, className: "bg-neutral/50" },
    { key: "pos", label: "Positive", value: counts.pos, className: "bg-gain" },
  ];
  return (
    <div>
      <div className="flex h-2.5 gap-[3px]" role="img" aria-label={parts.map((p) => `${p.label} ${Math.round((p.value / total) * 100)}%`).join(", ")}>
        {parts.map((p) => (
          <div key={p.key} className={cx("h-full rounded-full transition-[width] duration-500 ease-out", p.className)} style={{ width: `${(p.value / total) * 100}%` }} />
        ))}
      </div>
      <dl className="mt-5 grid grid-cols-3 gap-4">
        {parts.map((p) => (
          <div key={p.key}>
            <dt className="flex items-center gap-2 text-[13px] text-ink-3">
              <span className={cx("h-2 w-2 rounded-full", p.className)} aria-hidden="true" />
              {p.label}
            </dt>
            <dd className="figure mt-1.5 text-[20px] text-ink">{((p.value / total) * 100).toFixed(1)}%</dd>
            <dd className="num text-[12px] text-ink-3">{integer(p.value)} signals</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function SeverityCurve({ points, current, height = 220 }: { points: { impact: number; multiplier: number; pnl: number }[]; current: number; height?: number }) {
  const { palette } = useApp();
  const data = points.map((p) => ({ impact: p.impact, pnl: p.pnl / 1e6, multiplier: p.multiplier }));
  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        Stress P&L for event impact from {points[0]?.impact} to {points[points.length - 1]?.impact}: {data.map((d) => `${d.impact}: ${d.pnl.toFixed(1)}m`).join(", ")}.
      </figcaption>
      <div style={{ height }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 16, bottom: 4, left: -6 }}>
            <CartesianGrid stroke={palette.grid} vertical={false} />
            <XAxis dataKey="impact" type="number" domain={[7, 10]} ticks={[7, 7.5, 8, 8.5, 9, 9.5, 10]} tick={tick(palette)} axisLine={false} tickLine={false} />
            <YAxis tick={tick(palette)} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}m`} />
            <ReferenceLine x={current} stroke={palette.accent} strokeDasharray="4 4" />
            <Tooltip
              isAnimationActive={false}
              content={({ active, payload }) => {
                const row = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null;
                if (!row) return null;
                return (
                  <TooltipCard>
                    <div className="font-semibold">Impact {score(row.impact)} (multiplier ×{row.multiplier.toFixed(2)})</div>
                    <div className="num text-ink-2">{usdMillions(row.pnl * 1e6, 1, true)}</div>
                  </TooltipCard>
                );
              }}
            />
            <Line type="monotone" dataKey="pnl" stroke={palette.loss} strokeWidth={2.4} dot={{ r: 3.5, fill: palette.loss }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
