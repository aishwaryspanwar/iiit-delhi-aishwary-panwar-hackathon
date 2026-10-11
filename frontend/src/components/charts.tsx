import { useMemo, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useApp } from "../state";
import { integer, score, shortDay, signed, usdMillions, percent } from "../lib/format";
import { ASSET_TEXT, FACTOR_ORDER, FACTOR_TEXT, assetChange } from "../lib/risk";
import type { AssetBreakdown, DaySummary, Factor } from "../lib/types";
import type { ChartPalette } from "../lib/theme";
import { cx } from "./ui";

const FONT = "Google Sans Flex, sans-serif";

function tick(palette: ChartPalette, size = 11.5) {
  return { fontSize: size, fontFamily: FONT, fill: palette.ink3 };
}

function TooltipCard({ children }: { children: ReactNode }) {
  return <div className="overlay max-w-[320px] rounded-xl px-4 py-3 text-[12.5px] leading-relaxed text-ink">{children}</div>;
}

const FACTOR_SHORT: Record<Factor, string> = { rates: "Rates", spread: "Spread", migration: "Migration", equity: "Equity", vol: "Vol", second_order: "Convexity" };

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
    <text x={x} y={y} textAnchor={anchor} fontSize={12} fontWeight={400} fontFamily={FONT} fill={palette.ink2}>
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
    .map((row) => ({ label: ASSET_TEXT[row.asset_class], pnl: row.pnl / 1e6, raw: row, pct: assetChange(row) }));
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
                      P&L {usdMillions(row.raw.pnl, 2, true)}{row.pct !== null && <> ({percent(row.pct)})</>}
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
              <span className="num shrink-0 font-normal text-ink">{formatValue(row.value)}</span>
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
