import { useMemo, useRef, useState, type KeyboardEvent, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent } from "react";
import { geoGraticule10, geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import type { FeatureCollection } from "geojson";
import { Globe2, Minus, Plus, RotateCcw, X } from "lucide-react";
import worldTopology from "world-atlas/countries-110m.json";
import { api } from "../lib/api";
import { dateTime, integer, score, signed } from "../lib/format";
import { GEO_PLACES, placeName } from "../lib/geo";
import { BAND_LABELS, SOURCE_TEXT, type RiskBand } from "../lib/risk";
import type { GeoCountry } from "../lib/types";
import { useAsync } from "../lib/useAsync";
import { useApp } from "../state";
import { Select } from "./Select";
import { POSTURE_COPY, PostureGauge, RiskScale } from "./posture";
import { Segmented } from "./Segmented";
import { BandBadge, ClassTag, EmptyState, ErrorState, Stat, TONE_TEXT, cx, type Tone } from "./ui";

const WIDTH = 960;
const HEIGHT = 480;
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.6;
const DRAG_THRESHOLD = 3;
const LABELLED = 8;
const SENTIMENT_BAND = 0.1;
const PERIODS = [
  { value: 1, label: "Replay day" },
  { value: 7, label: "7 days" },
  { value: 0, label: "Window to date" },
];
const TABS: { id: SideTab; label: string }[] = [
  { id: "posture", label: "Risk posture" },
  { id: "covered", label: "Most covered" },
  { id: "stats", label: "Stats" },
];

type SideTab = "posture" | "covered" | "stats";

export interface MapPosture {
  value: number;
  band: RiskBand;
}

export interface MapStat {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
}

const projection = geoNaturalEarth1().fitExtent(
  [
    [6, 6],
    [WIDTH - 6, HEIGHT - 6],
  ],
  { type: "Sphere" },
);
const pathOf = geoPath(projection);
const topology = worldTopology as unknown as Topology<{ countries: GeometryCollection }>;
const SHAPES = (feature(topology, topology.objects.countries) as unknown as FeatureCollection).features.map((shape) => ({
  iso: String(shape.id),
  d: pathOf(shape) ?? "",
}));
const SPHERE = pathOf({ type: "Sphere" }) ?? "";
const GRATICULE = pathOf(geoGraticule10()) ?? "";

interface View {
  k: number;
  x: number;
  y: number;
}

interface Bubble extends GeoCountry {
  name: string;
  cx: number;
  cy: number;
  r: number;
}

function clampView(view: View): View {
  const k = Math.min(MAX_ZOOM, Math.max(1, view.k));
  return { k, x: Math.min(0, Math.max(WIDTH * (1 - k), view.x)), y: Math.min(0, Math.max(HEIGHT * (1 - k), view.y)) };
}

function zoomAround(view: View, factor: number, cx = WIDTH / 2, cy = HEIGHT / 2): View {
  const k = Math.min(MAX_ZOOM, Math.max(1, view.k * factor));
  return clampView({ k, x: cx - ((cx - view.x) * k) / view.k, y: cy - ((cy - view.y) * k) / view.k });
}

function sentimentTone(value: number): "loss" | "gain" | "neutral" {
  if (value <= -SENTIMENT_BAND) return "loss";
  if (value >= SENTIMENT_BAND) return "gain";
  return "neutral";
}

const TONE_WORD = { loss: "negative", gain: "positive", neutral: "neutral" } as const;
const TONE_LABEL = { loss: "Negative", gain: "Positive", neutral: "Neutral" } as const;

export function WorldMap({ posture, stats }: { posture: MapPosture; stats: MapStat[] }) {
  const { dataset, replay, revision, palette, openDetail, className, summary } = useApp();
  const threshold = summary.trigger_settings.impact_threshold;
  const [days, setDays] = useState(0);
  const [tab, setTab] = useState<SideTab>("posture");
  const [selected, setSelected] = useState<string | null>(null);
  const [hover, setHover] = useState<{ code: string; left: number; top: number } | null>(null);
  const [view, setView] = useState<View>({ k: 1, x: 0, y: 0 });
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; start: View; moved: boolean } | null>(null);

  const geo = useAsync(replay.day ? (signal) => api.geo(dataset, replay.day, days, signal) : null, [dataset, replay.day, days, revision]);
  const countries = useMemo(() => geo.data?.countries ?? [], [geo.data]);
  const byCode = useMemo(() => new Map(countries.map((c) => [c.code, c])), [countries]);

  const bubbles = useMemo<Bubble[]>(() => {
    const top = Math.max(1, ...countries.map((c) => c.signals));
    return countries
      .filter((c) => GEO_PLACES[c.code])
      .map((c) => {
        const place = GEO_PLACES[c.code];
        const [cx, cy] = projection([place.lon, place.lat]) ?? [0, 0];
        return { ...c, name: place.name, cx, cy, r: 3.5 + 17 * Math.sqrt(c.signals / top) };
      })
      .sort((a, b) => b.signals - a.signals);
  }, [countries]);

  const shading = useMemo(() => {
    const top = Math.log1p(Math.max(1, ...countries.map((c) => c.signals)));
    const result = new Map<string, number>();
    for (const c of countries) {
      const iso = GEO_PLACES[c.code]?.iso;
      if (iso) result.set(iso, Math.log1p(c.signals) / top);
    }
    return result;
  }, [countries]);

  const colours = { loss: palette.loss, gain: palette.gain, neutral: palette.neutral };
  const active = selected ? byCode.get(selected) ?? null : null;
  const hovered = hover ? byCode.get(hover.code) ?? null : null;

  const toViewBox = (clientX: number, clientY: number) => {
    const box = frame.current?.getBoundingClientRect();
    if (!box || !box.width) return { x: 0, y: 0, scale: 1 };
    const scale = WIDTH / box.width;
    return { x: (clientX - box.left) * scale, y: (clientY - box.top) * scale, scale };
  };

  const onPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, start: view, moved: false };
  };

  const onPointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const state = drag.current;
    if (!state) return;
    const dx = event.clientX - state.x;
    const dy = event.clientY - state.y;
    if (!state.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    if (!state.moved) event.currentTarget.setPointerCapture(event.pointerId);
    state.moved = true;
    const { scale } = toViewBox(event.clientX, event.clientY);
    setHover(null);
    setView(clampView({ ...state.start, x: state.start.x + dx * scale, y: state.start.y + dy * scale }));
  };

  const endDrag = () => {
    window.setTimeout(() => {
      drag.current = null;
    }, 0);
  };

  const select = (code: string) => {
    setTab("covered");
    setSelected((current) => (current === code ? null : code));
  };

  const choose = (code: string) => {
    if (drag.current?.moved) return;
    select(code);
  };

  const onBubbleKey = (event: KeyboardEvent<SVGGElement>, code: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      select(code);
    }
  };

  const showHover = (code: string, clientX: number, clientY: number) => {
    const box = frame.current?.getBoundingClientRect();
    if (!box || drag.current?.moved) return;
    setHover({ code, left: clientX - box.left, top: clientY - box.top });
  };

  const onDoubleClick = (event: ReactMouseEvent<SVGSVGElement>) => {
    const point = toViewBox(event.clientX, event.clientY);
    setView((current) => zoomAround(current, ZOOM_STEP, point.x, point.y));
  };

  return (
    <section data-tour="map" className="panel col-span-12 flex min-w-0 flex-col" aria-labelledby="world-map-title">
      <header className="px-5 pt-5 md:px-6">
        <h2 id="world-map-title" className="text-[15.5px] leading-snug font-semibold text-ink">
          Where the news is
        </h2>
        <p className="mt-1 text-[13px] leading-snug text-ink-3">Countries named in the headlines. Bigger bubbles mean more coverage.</p>
      </header>

      <div className="grid min-w-0 gap-5 px-5 pt-4 md:px-6 xl:grid-cols-[minmax(0,1fr)_minmax(340px,394px)] 3xl:grid-cols-[minmax(0,1fr)_minmax(400px,460px)]">
        <div className="min-w-0">
          <div ref={frame} className="relative w-full overflow-hidden rounded-2xl bg-surface-2" style={{ aspectRatio: `${WIDTH} / ${HEIGHT}` }}>
            {geo.error && !geo.data ? (
              <div className="absolute inset-0 flex items-center justify-center p-6">
                <ErrorState error={geo.error} onRetry={geo.reload} compact />
              </div>
            ) : (
              <svg
                viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                className={cx("block h-full w-full touch-none select-none", view.k > 1 ? "cursor-grab active:cursor-grabbing" : "cursor-default")}
                aria-label="World map of headlines by country"
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
                onPointerLeave={() => setHover(null)}
                onDoubleClick={onDoubleClick}
              >
                <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
                  <path d={SPHERE} fill="transparent" stroke="var(--chart-grid)" vectorEffect="non-scaling-stroke" />
                  <path d={GRATICULE} fill="none" stroke="var(--chart-grid)" strokeOpacity={0.5} vectorEffect="non-scaling-stroke" />
                  {SHAPES.map((shape, index) => {
                    const intensity = shading.get(shape.iso);
                    const isSelected = active !== null && GEO_PLACES[active.code]?.iso === shape.iso;
                    return (
                      <path
                        key={`${shape.iso}-${index}`}
                        d={shape.d}
                        fill={intensity ? "var(--teal)" : "var(--surface-3)"}
                        fillOpacity={intensity ? 0.14 + 0.5 * intensity : 1}
                        stroke={isSelected ? "var(--accent)" : "var(--chart-grid)"}
                        strokeWidth={isSelected ? 1.6 : 0.6}
                        vectorEffect="non-scaling-stroke"
                      />
                    );
                  })}
                  {bubbles.map((bubble, index) => {
                    const tone = sentimentTone(bubble.mean_sentiment);
                    const hot = bubble.max_impact > threshold;
                    const isSelected = bubble.code === selected;
                    return (
                      <g
                        key={bubble.code}
                        role="button"
                        tabIndex={0}
                        aria-pressed={isSelected}
                        aria-label={`${bubble.name}: ${integer(bubble.signals)} headlines, ${TONE_WORD[tone]} on average (${signed(bubble.mean_sentiment)}), peak impact ${score(bubble.max_impact)}`}
                        className="cursor-pointer outline-none [&:focus-visible>circle]:stroke-[var(--accent)]"
                        onClick={() => choose(bubble.code)}
                        onKeyDown={(event) => onBubbleKey(event, bubble.code)}
                        onPointerEnter={(event) => showHover(bubble.code, event.clientX, event.clientY)}
                        onPointerMove={(event) => showHover(bubble.code, event.clientX, event.clientY)}
                        onPointerLeave={() => setHover(null)}
                        onFocus={() => setHover(null)}
                      >
                        <circle
                          cx={bubble.cx}
                          cy={bubble.cy}
                          r={bubble.r / view.k}
                          fill={colours[tone]}
                          fillOpacity={isSelected ? 0.95 : 0.72}
                          stroke={hot ? "var(--accent)" : "var(--surface)"}
                          strokeWidth={hot || isSelected ? 2.2 : 1}
                          vectorEffect="non-scaling-stroke"
                        />
                        {index < LABELLED && (
                          <text
                            x={bubble.cx + (bubble.r + 3) / view.k}
                            y={bubble.cy + 4 / view.k}
                            fontSize={11 / view.k}
                            fontWeight={600}
                            fill="var(--ink-2)"
                            stroke="var(--surface-2)"
                            strokeWidth={3 / view.k}
                            paintOrder="stroke"
                            pointerEvents="none"
                          >
                            {bubble.code}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}

            {hover && hovered && (
              <div
                className="pointer-events-none absolute z-10 w-[240px] rounded-xl border border-[var(--glass-border)] bg-surface px-3.5 py-3 text-[12.5px] shadow-hover"
                style={{ left: Math.min(hover.left + 14, (frame.current?.clientWidth ?? 0) - 250), top: Math.max(8, hover.top - 12) }}
                role="status"
              >
                <p className="text-[13.5px] font-semibold text-ink">{placeName(hovered.code)}</p>
                <p className="num mt-1 text-ink-2">{integer(hovered.signals)} headlines · peak impact {score(hovered.max_impact)}</p>
                <p className="num text-ink-3">
                  Mean sentiment {signed(hovered.mean_sentiment)} · mostly {className(hovered.top_class).toLowerCase()}
                </p>
                <p className="mt-1.5 line-clamp-2 text-ink-2">{hovered.headlines[0]?.text}</p>
              </div>
            )}

            {geo.data && bubbles.length === 0 && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <p className="rounded-full bg-surface px-4 py-2 text-[13px] text-ink-3">No located headlines in this period</p>
              </div>
            )}

            <div className="absolute right-3 bottom-3 flex flex-col gap-1.5">
              <button type="button" className="btn icon-btn" aria-label="Zoom in" title="Zoom in" onClick={() => setView((v) => zoomAround(v, ZOOM_STEP))}>
                <Plus size={15} aria-hidden="true" />
              </button>
              <button type="button" className="btn icon-btn" aria-label="Zoom out" title="Zoom out" onClick={() => setView((v) => zoomAround(v, 1 / ZOOM_STEP))}>
                <Minus size={15} aria-hidden="true" />
              </button>
              <button type="button" className="btn icon-btn" aria-label="Reset view" title="Reset view" onClick={() => setView({ k: 1, x: 0, y: 0 })}>
                <RotateCcw size={15} aria-hidden="true" />
              </button>
            </div>
          </div>

        </div>

        <aside className="relative min-w-0 rounded-2xl bg-surface-2" aria-label="Risk posture, coverage and key figures">
          <div className="flex min-h-[380px] flex-col gap-4 p-4 xl:absolute xl:inset-0 xl:min-h-0">
            <Segmented options={TABS} value={tab} onChange={setTab} label="Map side panel" idPrefix="map-side" />
            <div id="map-side-panel" role="tabpanel" aria-labelledby={`map-side-tab-${tab}`} className="flex min-h-0 flex-1 flex-col">
              {tab === "posture" && (
                <>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[12.5px] text-ink-3">Peak event impact, last 72 hours</p>
                    <BandBadge band={posture.band} />
                  </div>
                  <div className="flex flex-1 flex-col items-center justify-center gap-5 py-4 text-center">
                    <PostureGauge value={posture.value} band={posture.band} size={186} />
                    <div className="flex max-w-[300px] flex-col gap-2">
                      <p className={cx("figure text-[26px]", TONE_TEXT[posture.band])}>{BAND_LABELS[posture.band]} risk</p>
                      <p className="text-[13px] leading-relaxed text-ink-2">{POSTURE_COPY[posture.band]}</p>
                    </div>
                    <RiskScale value={posture.value} threshold={threshold} />
                  </div>
                </>
              )}

              {tab === "covered" && (
                <>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      {active ? (
                        <>
                          <p className="caption">Selected country</p>
                          <h3 className="mt-0.5 truncate text-[15px] font-semibold text-ink">{placeName(active.code)}</h3>
                        </>
                      ) : (
                        <h3 className="text-[14px] font-semibold text-ink">Most covered</h3>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {selected && (
                        <button type="button" className="btn icon-btn h-[34px] w-[34px]" aria-label="Clear selection" title="All countries" onClick={() => setSelected(null)}>
                          <X size={14} aria-hidden="true" />
                        </button>
                      )}
                      <Select options={PERIODS} value={days} onChange={setDays} label="Map period" />
                    </div>
                  </div>

                  {active && (
                    <>
                      <p className="num mt-1.5 text-[12.5px] text-ink-3">
                        {integer(active.signals)} headlines · mean sentiment {signed(active.mean_sentiment)} · peak {score(active.max_impact)}
                      </p>
                      <ul className="-mx-2 mt-2 flex min-h-0 flex-1 flex-col overflow-y-auto pb-4 [mask-image:linear-gradient(to_bottom,#000_calc(100%-28px),transparent)]">
                        {active.headlines.map((headline) => (
                          <li key={headline.signal_id}>
                            <button
                              type="button"
                              onClick={() => openDetail({ kind: "signal", id: headline.signal_id })}
                              className="flex w-full items-start gap-3 rounded-xl px-2 py-2.5 text-left transition-colors duration-150 hover:bg-surface-3"
                            >
                              <span className="min-w-0 flex-1">
                                <span className="line-clamp-2 text-[13.5px] leading-snug text-ink">{headline.text}</span>
                                <span className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12px] text-ink-3">
                                  <span className="num">{dateTime(headline.published_at)}</span>
                                  <span>{headline.outlet ?? SOURCE_TEXT[headline.source] ?? headline.source}</span>
                                  <ClassTag label={className(headline.class)} />
                                </span>
                              </span>
                              <span className={cx("figure shrink-0 text-[15px]", headline.impact > threshold ? "text-critical" : "text-ink")}>{score(headline.impact)}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                      {active.signals > active.headlines.length && (
                        <p className="mt-2 text-[12px] text-ink-3">Showing the {active.headlines.length} highest-impact of {integer(active.signals)} headlines.</p>
                      )}
                    </>
                  )}

                  {!active && selected && (
                    <div className="flex flex-1 items-center">
                      <EmptyState title={`No headlines name ${placeName(selected)} in this period`} body="Pick a longer period or another country." icon={<Globe2 size={18} />} />
                    </div>
                  )}

                  {!selected && <p className="mt-1.5 text-[12.5px] text-ink-3">Select a country to read its headlines.</p>}

                  {!selected && (
                    <ul className="-mx-2 mt-2 flex min-h-0 flex-1 flex-col overflow-y-auto pb-4 [mask-image:linear-gradient(to_bottom,#000_calc(100%-28px),transparent)]">
                      {countries.slice(0, 12).map((country) => (
                        <li key={country.code}>
                          <button
                            type="button"
                            onClick={() => select(country.code)}
                            className="flex w-full items-center gap-3 rounded-xl px-2 py-[7px] text-left transition-colors duration-150 hover:bg-surface-3"
                          >
                            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colours[sentimentTone(country.mean_sentiment)] }} aria-hidden="true" />
                            <span className="min-w-0 flex-1 truncate text-[13.5px] text-ink">{placeName(country.code)}</span>
                            <span className="h-1.5 w-20 shrink-0 overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
                              <span className="block h-full rounded-full bg-teal" style={{ width: `${(100 * country.signals) / Math.max(1, countries[0].signals)}%` }} />
                            </span>
                            <span className="num w-12 shrink-0 text-right text-[12.5px] text-ink-2">{integer(country.signals)}</span>
                          </button>
                        </li>
                      ))}
                      {geo.data && countries.length === 0 && <li className="px-2 py-2 text-[13px] text-ink-3">No located headlines in this period.</li>}
                    </ul>
                  )}
                </>
              )}

              {tab === "stats" && (
                <div className="flex flex-1 flex-col gap-3">
                  <div className="grid flex-1 grid-cols-2 grid-rows-2 gap-3">
                    {stats.map((item) => (
                      <div key={item.label} className="flex min-w-0 flex-col justify-center rounded-[14px] border border-line bg-surface-2 px-4 py-3">
                        <Stat label={item.label} value={item.value} sub={item.sub} tone={item.tone} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>

      <div className="px-5 pt-3 pb-6 md:px-6">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[12.5px] text-ink-3">
          {(["loss", "neutral", "gain"] as const).map((tone) => (
            <span key={tone} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: colours[tone] }} aria-hidden="true" />
              {TONE_LABEL[tone]}
            </span>
          ))}
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full border-2 border-[var(--accent)]" aria-hidden="true" />
            Impact above {threshold}
          </span>
        </div>
      </div>
    </section>
  );
}
