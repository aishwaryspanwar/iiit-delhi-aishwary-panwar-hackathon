import { BAND_LABELS, MODERATE_FROM, criticalFrom, type RiskBand } from "../lib/risk";
import { TONE_TEXT, cx } from "./ui";

export const POSTURE_COPY: Record<RiskBand, string> = {
  low: "No event cluster in the last three days scores above the moderate band.",
  moderate: "News flow is elevated, but nothing is close to the stress-test trigger.",
  high: "At least one event cluster is above the trigger threshold.",
  critical: "A severe event cluster is in the window; scenario shocks would apply near full strength.",
};

const GAUGE_TONE: Record<RiskBand, string> = { low: "text-low", moderate: "text-moderate-mark", high: "text-high", critical: "text-critical" };
const BAND_FILL: Record<RiskBand, string> = { low: "bg-low", moderate: "bg-moderate-mark", high: "bg-high", critical: "bg-critical" };

export function PostureGauge({ value, band, size = 150 }: { value: number; band: RiskBand; size?: number }) {
  const fraction = Math.max(0, Math.min(1, (value - 1) / 9));
  const circumference = Math.PI * 64;
  return (
    <svg viewBox="0 0 152 88" style={{ width: size, height: (size * 88) / 152 }} className={cx("shrink-0", GAUGE_TONE[band])} aria-hidden="true">
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
      <text x="76" y="76" textAnchor="middle" fontSize="34" fontWeight={600} fill="var(--ink)" fontFamily="Google Sans Flex, sans-serif">
        {value.toFixed(1)}
      </text>
    </svg>
  );
}

export function RiskScale({ value, threshold }: { value: number; threshold: number }) {
  const critical = criticalFrom(threshold);
  const bands: [RiskBand, number, number][] = [
    ["low", 1, MODERATE_FROM],
    ["moderate", MODERATE_FROM, threshold],
    ["high", threshold, critical],
    ["critical", critical, 10],
  ];
  const position = Math.max(0, Math.min(1, (value - 1) / 9)) * 100;
  return (
    <div className="w-full max-w-[300px]" role="img" aria-label={`Risk scale: ${value.toFixed(1)} on a 1 to 10 scale; moderate from ${MODERATE_FROM}, high above ${threshold}, critical from ${critical}`}>
      <div className="relative pt-3">
        <span
          className="absolute top-0 h-0 w-0 -translate-x-1/2 border-x-[5px] border-t-[6px] border-x-transparent border-t-[var(--ink)]"
          style={{ left: `${position}%` }}
          aria-hidden="true"
        />
        <div className="flex gap-1" aria-hidden="true">
          {bands.map(([band, from, to]) => {
            const active = value >= from && (value < to || (band === "critical" && value <= to));
            return (
              <div key={band} className="flex min-w-0 flex-col items-center gap-1.5" style={{ flex: `${to - from} 1 0` }}>
                <span className={cx("h-1.5 w-full rounded-full", BAND_FILL[band], !active && "opacity-25")} />
                <span className={cx("truncate text-[11.5px]", active ? cx("font-semibold", TONE_TEXT[band]) : "text-ink-3")}>{BAND_LABELS[band]}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
