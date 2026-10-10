import { useMemo, useState, type ReactNode } from "react";
import { ArrowRight, ArrowUpDown, ChevronDown, ChevronUp } from "lucide-react";
import { useApp } from "../state";
import { basisPoints, day, integer, percent, score, signed, usdMillions } from "../lib/format";
import { ASSET_TEXT, FACTOR_ORDER, FACTOR_TEXT, SCOPE_TEXT, impactBand } from "../lib/risk";
import type { AppliedShocks, PositionResult, RunSummary, ScenarioShocks, StressDetail, Totals } from "../lib/types";
import { BandBadge, ClassTag, cx } from "./ui";

function ChainStep({ index, label, title, children, tone = "default" }: { index: number; label: string; title: ReactNode; children?: ReactNode; tone?: "default" | "loss" }) {
  return (
    <li className="relative flex min-w-0 flex-1 flex-col">
      <div className={cx("flex h-full min-w-0 flex-col gap-2 rounded-xl px-4 py-4", tone === "loss" ? "bg-loss/10" : "bg-surface-2")}>
        <div className="flex items-center gap-2.5">
          <span
            className={cx(
              "num flex h-[22px] w-[22px] items-center justify-center rounded-full text-[11.5px] font-semibold",
              tone === "loss" ? "bg-loss text-white" : "bg-teal text-on-teal",
            )}
          >
            {index}
          </span>
          <span className="text-[12.5px] font-medium text-ink-3">{label}</span>
        </div>
        <div className="min-w-0 text-[14px] leading-snug font-semibold text-ink">{title}</div>
        {children && <div className="min-w-0 text-[12.5px] leading-snug text-ink-3">{children}</div>}
      </div>
    </li>
  );
}

function Connector() {
  return (
    <li aria-hidden="true" className="hidden shrink-0 items-center justify-center text-ink-3 @5xl:flex @5xl:w-5">
      <ArrowRight size={14} />
    </li>
  );
}

export function CausalChain({ detail }: { detail: StressDetail }) {
  const { className, meta } = useApp();
  const { run, event, representative_signals: reps } = detail;
  const shocks = run.shocks_applied;
  const rules = [...new Set(reps.flatMap((s) => s.event.matched_rules))].sort((a, b) => a.localeCompare(b));
  const threshold = detail.trigger_settings.impact_threshold;
  const lead = event.lead;
  return (
    <div className="@container">
      <ol className="grid grid-cols-1 gap-3 @lg:grid-cols-2 @3xl:grid-cols-3 @5xl:flex @5xl:flex-row @5xl:items-stretch @5xl:gap-1.5" aria-label="Causal chain from news event to portfolio impact">
        <ChainStep index={1} label="Event" title={<span className="line-clamp-2">“{lead?.text ?? "n/a"}”</span>}>
          {day(event.t_start)}, {integer(event.n_items)} items from {integer(event.n_outlets)} outlets
        </ChainStep>
        <Connector />
        <ChainStep index={2} label="Classification" title={className(event.class)}>
          Confidence <span className="num">{event.confidence_mean.toFixed(2)}</span>, rules <span className="num">{rules.join(", ") || "none"}</span>
        </ChainStep>
        <Connector />
        <ChainStep
          index={3}
          label="Impact"
          title={
            <span className="flex flex-wrap items-center gap-2">
              <span className="figure text-[18px]">{score(event.impact)}</span>
              <BandBadge band={impactBand(event.impact, threshold)} />
            </span>
          }
        >
          Above the trigger threshold of {threshold}; every check passed
        </ChainStep>
        <Connector />
        <ChainStep index={4} label="Scenario" title={`${className(run.class)}, ${SCOPE_TEXT[run.scope].toLowerCase()} scope`}>
          Severity ×{shocks.multiplier.toFixed(2)} (floor {meta.severity.floor_multiplier}), targeting {detail.summary.scope_label}
        </ChainStep>
        <Connector />
        <ChainStep index={5} label="Shock" title={<span className="num">{percent(shocks.equity_market, 1)} equities, {basisPoints(shocks.rates_bp)}</span>}>
          <span className="num">
            IG {basisPoints(shocks.spread_bp.IG)}, HY {basisPoints(shocks.spread_bp.HY)}, vol {signed(shocks.vol_pts, 1)} pts
            {shocks.in_scope.spread_bp !== 0 && <>, in-scope {basisPoints(shocks.in_scope.spread_bp)} and {shocks.in_scope.rating_notches} notch</>}
          </span>
        </ChainStep>
        <Connector />
        <ChainStep
          index={6}
          label="Portfolio impact"
          tone="loss"
          title={
            <span className="figure text-[18px] text-loss">
              {usdMillions(run.totals.pnl)} <span className="text-[13px]">{percent(run.totals.pnl_pct)}</span>
            </span>
          }
        >
          {integer(run.in_scope_positions)} in-scope of {run.positions.length} positions revalued
        </ChainStep>
      </ol>
    </div>
  );
}

export function BeforeAfter({ totals, size = "lg" }: { totals: Totals; size?: "lg" | "sm" }) {
  const big = size === "lg" ? "text-[25px]" : "text-[18px]";
  const changeTone = totals.pnl < 0 ? "text-loss" : "text-gain";
  return (
    <div className="@container">
      <dl className="grid grid-cols-1 gap-x-6 gap-y-4 @md:grid-cols-3">
        <div className="min-w-0">
          <dt className="caption mb-2">Before stress</dt>
          <dd className={cx("figure whitespace-nowrap text-ink", big)}>{usdMillions(totals.value_before)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="caption mb-2">After stress</dt>
          <dd className={cx("figure whitespace-nowrap text-ink", big)}>{usdMillions(totals.value_after)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="caption mb-2">Change</dt>
          <dd className={cx("figure whitespace-nowrap", big, changeTone)}>{usdMillions(totals.pnl, 1, true)}</dd>
          <dd className={cx("num mt-1 text-[13px] font-medium", changeTone)}>{percent(totals.pnl_pct)} of portfolio value</dd>
        </div>
      </dl>
    </div>
  );
}

const TH = "caption py-3 pr-4 text-left font-medium";

export function AssetTable({ detail }: { detail: StressDetail }) {
  const rows = [...detail.run.by_asset_class].sort((a, b) => a.pnl - b.pnl);
  const maxLoss = Math.max(...rows.map((r) => Math.abs(r.pnl)), 1);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-[13.5px]">
        <caption className="sr-only">Portfolio value before and after stress by asset class</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Asset class</th>
            <th scope="col" className={cx(TH, "text-right")}>Before</th>
            <th scope="col" className={cx(TH, "text-right")}>After</th>
            <th scope="col" className={cx(TH, "text-right")}>P&L</th>
            <th scope="col" className={cx(TH, "pr-0 text-right")}>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.asset_class} className="border-b border-line last:border-b-0">
              <th scope="row" className="py-3.5 pr-4 text-left font-medium text-ink">{ASSET_TEXT[row.asset_class]}</th>
              <td className="num py-3.5 pr-4 text-right text-ink-2">{usdMillions(row.value_before)}</td>
              <td className="num py-3.5 pr-4 text-right text-ink-2">{usdMillions(row.value_after)}</td>
              <td className="py-3.5 pr-4">
                <div className="flex items-center justify-end gap-3">
                  <div className="hidden h-[5px] w-24 justify-end rounded-full bg-surface-3 sm:flex" aria-hidden="true">
                    <div className={cx("h-full rounded-full", row.pnl < 0 ? "bg-loss" : "bg-gain")} style={{ width: `${(Math.abs(row.pnl) / maxLoss) * 100}%` }} />
                  </div>
                  <span className={cx("num w-20 text-right font-medium", row.pnl < 0 ? "text-loss" : "text-gain")}>{usdMillions(row.pnl, 1, true)}</span>
                </div>
              </td>
              <td className="num py-3.5 text-right text-ink-3">{row.value_before ? percent(row.pnl / Math.abs(row.value_before)) : "n/a"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type ShockRow = { label: string; base: string; applied: string };

function shockRows(base: ScenarioShocks | null, applied: AppliedShocks): ShockRow[] {
  const pct = (v: number) => percent(v, 1);
  const rows: ShockRow[] = [
    { label: "Equity market (× beta)", base: base ? pct(base.equity_market) : "—", applied: pct(applied.equity_market) },
    { label: "Risk-free rates", base: base ? basisPoints(base.rates_bp) : "—", applied: basisPoints(applied.rates_bp) },
    { label: "IG credit spreads", base: base ? basisPoints(base.spread_bp.IG) : "—", applied: basisPoints(applied.spread_bp.IG) },
    { label: "HY credit spreads", base: base ? basisPoints(base.spread_bp.HY) : "—", applied: basisPoints(applied.spread_bp.HY) },
    { label: "Implied volatility", base: base ? `${signed(base.vol_pts, 1)} pts` : "—", applied: `${signed(applied.vol_pts, 1)} pts` },
    { label: "In-scope spread add-on", base: base ? basisPoints(base.in_scope.spread_bp) : "—", applied: basisPoints(applied.in_scope.spread_bp) },
    { label: "In-scope rating change", base: base ? `${base.in_scope.rating_notches} notch` : "—", applied: `${applied.in_scope.rating_notches} notch` },
    { label: "In-scope equity excess", base: base ? pct(base.in_scope.equity_excess) : "—", applied: pct(applied.in_scope.equity_excess) },
  ];
  for (const [sector, value] of Object.entries(applied.sector_excess)) {
    const baseValue = base?.sector_excess[sector];
    rows.push({ label: `Sector excess, ${sector.replace("_", " ")}`, base: baseValue === undefined ? "—" : pct(baseValue), applied: pct(value) });
  }
  return rows;
}

export function ShockTable({ detail }: { detail: StressDetail }) {
  const rows = shockRows(detail.base_scenario, detail.run.shocks_applied);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13.5px]">
        <caption className="sr-only">Scenario shocks before and after severity scaling</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className={TH}>Risk factor</th>
            <th scope="col" className={cx(TH, "text-right whitespace-nowrap")}>Base</th>
            <th scope="col" className={cx(TH, "pr-0 text-right whitespace-nowrap")}>Applied ×{detail.run.shocks_applied.multiplier.toFixed(2)}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-b border-line last:border-b-0">
              <th scope="row" className="py-2.5 pr-4 text-left font-normal text-ink-2">{row.label}</th>
              <td className="num py-2.5 pr-4 text-right whitespace-nowrap text-ink-3">{row.base}</td>
              <td className="num py-2.5 text-right font-semibold whitespace-nowrap text-ink">{row.applied}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type SortKey = "pnl" | "value_before" | "position_id";
type SortState = { key: SortKey; dir: 1 | -1 };

function SortHeader({ label, column, sort, onSort, align = "left" }: { label: string; column: SortKey; sort: SortState; onSort: (key: SortKey) => void; align?: "left" | "right" }) {
  const active = sort.key === column;
  let icon = <ArrowUpDown size={12} aria-hidden="true" />;
  let ariaSort: "ascending" | "descending" | "none" = "none";
  if (active) {
    icon = sort.dir === 1 ? <ChevronUp size={13} aria-hidden="true" /> : <ChevronDown size={13} aria-hidden="true" />;
    ariaSort = sort.dir === 1 ? "ascending" : "descending";
  }
  return (
    <th scope="col" aria-sort={ariaSort} className={cx("py-3 pr-4", align === "right" && "text-right")}>
      <button
        type="button"
        className={cx("inline-flex items-center gap-1.5 rounded-md text-[12.5px] font-medium transition-colors hover:text-ink", active ? "text-ink" : "text-ink-3")}
        onClick={() => onSort(column)}
      >
        {label} {icon}
      </button>
    </th>
  );
}

function rateSpreadText(p: PositionResult): string {
  if (p.d_rate_bp || p.d_spread_bp) return `${signed(p.d_rate_bp, 0)} / ${signed(p.d_spread_bp + p.d_migration_spread_bp, 0)}`;
  if (p.equity_return) return percent(p.equity_return, 1);
  return "—";
}

function pnlTone(value: number): string {
  if (value < 0) return "text-loss";
  if (value > 0) return "text-gain";
  return "text-ink-3";
}

export function PositionsTable({ positions }: { positions: PositionResult[] }) {
  const [sort, setSort] = useState<SortState>({ key: "pnl", dir: 1 });
  const [inScopeOnly, setInScopeOnly] = useState(false);
  const rows = useMemo(() => {
    const filtered = inScopeOnly ? positions.filter((p) => p.in_scope) : positions;
    return [...filtered].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const diff = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return diff * sort.dir;
    });
  }, [positions, sort, inScopeOnly]);
  const toggle = (key: SortKey) =>
    setSort((current) => {
      if (current.key === key) return { key, dir: current.dir === 1 ? -1 : 1 };
      return { key, dir: key === "pnl" ? 1 : -1 };
    });
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex gap-1.5">
          <button type="button" className="chip" aria-pressed={!inScopeOnly} onClick={() => setInScopeOnly(false)}>
            All positions
          </button>
          <button type="button" className="chip" aria-pressed={inScopeOnly} onClick={() => setInScopeOnly(true)}>
            In scope only
          </button>
        </div>
        <span className="num text-[12.5px] text-ink-3">{rows.length} positions</span>
      </div>
      <div className="max-h-[460px] overflow-auto">
        <table className="w-full min-w-[700px] border-collapse text-[13px]">
          <caption className="sr-only">Position-level stress results</caption>
          <thead className="sticky top-0 z-10 bg-surface-solid">
            <tr className="border-b border-line text-left">
              <SortHeader label="Position" column="position_id" sort={sort} onSort={toggle} />
              <th scope="col" className={TH}>Class</th>
              <th scope="col" className={TH}>Sector, country</th>
              <th scope="col" className={TH}>Rating</th>
              <SortHeader label="Value" column="value_before" sort={sort} onSort={toggle} align="right" />
              <th scope="col" className={cx(TH, "text-right")}>Δ rate / spread</th>
              <SortHeader label="P&L" column="pnl" sort={sort} onSort={toggle} align="right" />
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const top = FACTOR_ORDER.map((f) => ({ f, v: p[f] })).sort((a, b) => a.v - b.v)[0];
              return (
                <tr key={p.position_id} className="row-hover border-b border-line last:border-b-0">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2.5">
                      <span className={cx("h-2 w-2 shrink-0 rounded-full", p.in_scope ? "bg-high" : "bg-transparent")} title={p.in_scope ? "In scope of the event" : undefined} />
                      {p.in_scope && <span className="sr-only">In scope.</span>}
                      <span className="num text-ink-3">{p.position_id}</span>
                      <span className="truncate font-medium text-ink">{p.name}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-ink-2">{ASSET_TEXT[p.asset_class]}</td>
                  <td className="py-3 pr-4 text-ink-2">
                    {p.sector}, <span className="num">{p.country}</span>
                  </td>
                  <td className="num py-3 pr-4 whitespace-nowrap text-ink-2">
                    {p.rating || "—"}
                    {p.rating_after && p.rating_after !== p.rating && <span className="font-medium text-high"> → {p.rating_after}</span>}
                  </td>
                  <td className="num py-3 pr-4 text-right text-ink-2">{usdMillions(p.value_before)}</td>
                  <td className="num py-3 pr-4 text-right text-ink-3">{rateSpreadText(p)}</td>
                  <td className="py-3 pr-4 text-right whitespace-nowrap" title={top && top.v < 0 ? `Largest driver: ${FACTOR_TEXT[top.f]}` : undefined}>
                    <span className={cx("num font-medium", pnlTone(p.pnl))}>{usdMillions(p.pnl, 2, true)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-4 flex items-center gap-2 text-[12.5px] text-ink-3">
        <span className="h-2 w-2 shrink-0 rounded-full bg-high" aria-hidden="true" />
        In scope of the event by country, sector or name. Rate and spread moves are in basis points; equities show the applied return.
      </p>
    </div>
  );
}

export function RunPicker({ runs, selected, onSelect }: { runs: RunSummary[]; selected: string | null; onSelect: (id: string) => void }) {
  const { className } = useApp();
  return (
    <ul className="flex flex-col gap-1" aria-label="Triggered stress tests">
      {runs.map((run) => {
        const active = run.cluster_id === selected;
        return (
          <li key={run.cluster_id}>
            <button
              type="button"
              onClick={() => onSelect(run.cluster_id)}
              aria-pressed={active}
              className={cx("w-full rounded-xl px-4 py-3.5 text-left transition-colors duration-150", active ? "bg-surface-3 ring-1 ring-accent/70" : "hover:bg-surface-2")}
            >
              <div className="flex items-center justify-between gap-3">
                <span className={cx("num text-[12.5px]", active ? "text-ink" : "text-ink-3")}>{day(run.t_start)}</span>
                <span className="num text-[13.5px] font-semibold text-loss">{usdMillions(run.totals.pnl)}</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <ClassTag label={className(run.class)} emphasis={active} />
                <span className="num text-[12.5px] text-ink-2">Impact {score(run.impact)}</span>
              </div>
              <p className="mt-2 line-clamp-2 text-[12.5px] leading-snug text-ink-3">{run.lead?.text ?? run.scope_label}</p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
