import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { useMemo, type CSSProperties } from "react";
import { useApp } from "../state";
import { dayWithWeekday, integer, shortDay } from "../lib/format";
import { cx } from "./ui";

export function ReplayBar() {
  const { replay, summary } = useApp();
  const days = summary.days;
  const fill = replay.last ? (replay.index / replay.last) * 100 : 100;
  const markers = useMemo(() => days.map((d, i) => ({ i, triggered: d.triggered, date: d.date })).filter((d) => d.triggered > 0), [days]);
  const current = days[replay.index];
  const style = { "--fill": `${fill}%` } as CSSProperties;
  if (!days.length) return null;
  return (
    <div className="panel flex flex-wrap items-center gap-x-6 gap-y-3 rounded-[28px] px-4 py-3 md:px-5" role="group" aria-label="Historical replay">
      <div className="flex items-center gap-1.5">
        <button type="button" className="btn btn-ghost icon-btn" onClick={() => replay.step(-1)} disabled={replay.index === 0} aria-label="Previous day">
          <SkipBack size={15} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="btn btn-primary h-11 w-11 p-0"
          onClick={replay.togglePlay}
          aria-label={replay.playing ? "Pause replay" : "Play replay"}
          aria-pressed={replay.playing}
        >
          {replay.playing ? <Pause size={16} fill="currentColor" aria-hidden="true" /> : <Play size={16} fill="currentColor" className="ml-0.5" aria-hidden="true" />}
        </button>
        <button type="button" className="btn btn-ghost icon-btn" onClick={() => replay.step(1)} disabled={replay.index === replay.last} aria-label="Next day">
          <SkipForward size={15} aria-hidden="true" />
        </button>
      </div>
      <div className="min-w-[170px]">
        <div className="flex items-center gap-2 text-[12.5px] text-ink-3">
          <span className={cx("h-1.5 w-1.5 rounded-full", replay.playing ? "pulse-dot bg-accent" : "bg-teal")} aria-hidden="true" />
          {replay.playing ? "Replaying" : "Replay date"}
        </div>
        <div className="figure mt-1 text-[17px] text-ink" aria-live="polite">
          {dayWithWeekday(replay.day)}
        </div>
      </div>
      <div className="relative min-w-[220px] flex-1 pt-3">
        <div className="pointer-events-none absolute inset-x-[8px] top-0 h-3" aria-hidden="true">
          {markers.map((m) => (
            <span
              key={m.date}
              title={`${shortDay(m.date)}: stress test triggered`}
              className={cx("absolute top-0 h-[7px] w-[7px] -translate-x-1/2 rotate-45 rounded-[1px] transition-opacity", m.i <= replay.index ? "bg-critical" : "bg-critical/30")}
              style={{ left: `${replay.last ? (m.i / replay.last) * 100 : 0}%` }}
            />
          ))}
        </div>
        <input
          type="range"
          className="range"
          min={0}
          max={replay.last}
          step={1}
          value={replay.index}
          onChange={(e) => replay.setIndex(Number(e.target.value))}
          style={style}
          aria-label="Replay up to day"
          aria-valuetext={dayWithWeekday(replay.day)}
        />
        <div className="num flex justify-between text-[11.5px] text-ink-3" aria-hidden="true">
          <span>{shortDay(days[0].date)}</span>
          <span>{shortDay(days[days.length - 1].date)}</span>
        </div>
      </div>
      <div className="hidden text-right xl:block">
        <div className="text-[12.5px] text-ink-3">Day {replay.index + 1} of {days.length}</div>
        <div className="num mt-1 text-[14px] text-ink-2">{current ? `${integer(current.signals)} new signals` : ""}</div>
      </div>
    </div>
  );
}
