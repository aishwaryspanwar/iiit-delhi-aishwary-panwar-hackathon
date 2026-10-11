import type { ReactNode } from "react";
import { Circle, CircleCheck, CircleMinus, CircleX, Diamond, Inbox, RefreshCw, ServerCrash, Triangle, TriangleAlert } from "lucide-react";
import type { ApiError } from "../lib/api";
import { BAND_LABELS, SENTIMENT_TEXT, STATUS_TEXT, impactBand, type RiskBand } from "../lib/risk";
import { score, signed } from "../lib/format";
import type { EventStatus, SentimentLabel } from "../lib/types";

export function cx(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(" ");
}

export function Panel({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
  tour,
  as: Tag = "section",
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  tour?: string;
  as?: "section" | "div" | "article" | "aside";
}) {
  return (
    <Tag data-tour={tour} className={cx("panel flex min-w-0 flex-col", className)}>
      {(title || description || actions) && (
        <header className="flex items-start justify-between gap-4 px-5 pt-5 md:px-6">
          <div className="min-w-0">
            {title && <h2 className="text-[15.5px] leading-snug font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-1 text-[13px] leading-snug text-ink-3">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cx("min-w-0 flex-1 px-5 pt-4 pb-6 md:px-6", bodyClassName)}>{children}</div>
    </Tag>
  );
}

export type Tone = "default" | "gain" | "loss" | "accent" | RiskBand;

export const TONE_TEXT: Record<Tone, string> = {
  default: "text-ink",
  gain: "text-gain",
  loss: "text-loss",
  accent: "text-accent-ink",
  low: "text-low",
  moderate: "text-moderate",
  high: "text-high",
  critical: "text-critical",
};

export function Stat({
  label,
  value,
  sub,
  tone = "default",
  size = "md",
}: {
  label: ReactNode;
  value: ReactNode;
  sub?: ReactNode;
  tone?: Tone;
  size?: "sm" | "md" | "lg";
}) {
  const sizes = { sm: "text-[19px]", md: "text-[26px]", lg: "text-[34px]" };
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span className="caption line-clamp-2">{label}</span>
      <span className={cx("figure truncate", sizes[size], TONE_TEXT[tone])}>{value}</span>
      {sub && <span className="truncate text-[12.5px] text-ink-3">{sub}</span>}
    </div>
  );
}

const BAND_CLASSES: Record<RiskBand, string> = {
  low: "text-low bg-low/12",
  moderate: "text-moderate bg-moderate-mark/14",
  high: "text-high bg-high/14",
  critical: "text-critical bg-critical/14",
};

const BAND_LEVEL: Record<RiskBand, number> = { low: 1, moderate: 2, high: 3, critical: 4 };

export function BandBadge({ band, size = "sm" }: { band: RiskBand; size?: "sm" | "md" }) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full font-semibold",
        size === "sm" ? "h-[22px] px-2.5 text-[11.5px]" : "h-7 px-3 text-[12.5px]",
        BAND_CLASSES[band],
      )}
    >
      <span className="flex items-end gap-[2px]" aria-hidden="true">
        {[1, 2, 3, 4].map((level) => (
          <span key={level} className={cx("w-[3px] rounded-full bg-current", level > BAND_LEVEL[band] && "opacity-25")} style={{ height: `${3 + level * 2}px` }} />
        ))}
      </span>
      {BAND_LABELS[band]}
    </span>
  );
}

const STATUS_CLASSES: Record<EventStatus, string> = {
  triggered: "text-critical bg-critical/12",
  blocked: "text-moderate bg-moderate-mark/14",
  below: "text-ink-2 bg-surface-2",
};

export function StatusIcon({ status, size = 12 }: { status: EventStatus; size?: number }) {
  if (status === "triggered") return <Diamond size={size} fill="currentColor" aria-hidden="true" />;
  if (status === "blocked") return <Triangle size={size} fill="currentColor" aria-hidden="true" />;
  return <Circle size={size} aria-hidden="true" />;
}

export function StatusBadge({ status }: { status: EventStatus }) {
  return (
    <span className={cx("inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-full px-2.5 text-[11.5px] font-semibold", STATUS_CLASSES[status])}>
      <StatusIcon status={status} size={10} />
      {STATUS_TEXT[status]}
    </span>
  );
}

export function SentimentValue({ value, label }: { value: number; label?: SentimentLabel }) {
  let tone = "text-ink-2";
  if (value <= -0.05) tone = "text-loss";
  else if (value >= 0.05) tone = "text-gain";
  return (
    <span className="inline-flex items-baseline gap-1.5" title={label ? SENTIMENT_TEXT[label] : undefined}>
      <span className={cx("num text-[13.5px] font-normal", tone)}>{signed(value)}</span>
      {label && <span className="text-[12px] text-ink-3">{SENTIMENT_TEXT[label]}</span>}
    </span>
  );
}

export function ClassTag({ label, emphasis = false }: { label: string; emphasis?: boolean }) {
  return (
    <span
      className={cx(
        "inline-flex h-[22px] max-w-full items-center truncate rounded-full px-2.5 text-[11.5px] font-normal",
        emphasis ? "bg-teal-soft text-teal-ink" : "bg-surface-2 text-ink-2",
      )}
    >
      {label}
    </span>
  );
}

const BAR_FILL: Record<RiskBand, string> = { low: "bg-low", moderate: "bg-moderate-mark", high: "bg-high", critical: "bg-critical" };

export function ImpactMeter({ value, threshold, compact = false }: { value: number; threshold: number; compact?: boolean }) {
  const band = impactBand(value, threshold);
  const fill = ((value - 1) / 9) * 100;
  const tick = ((threshold - 1) / 9) * 100;
  return (
    <div className="flex min-w-0 items-center gap-3" aria-label={`Impact ${score(value)} of 10`}>
      <span className={cx("num w-8 shrink-0 text-right text-[14px] font-semibold", TONE_TEXT[band])}>{score(value)}</span>
      <div className={cx("relative h-[5px] flex-1 rounded-full bg-surface-3", compact ? "min-w-10" : "min-w-20")} aria-hidden="true">
        <div className={cx("absolute inset-y-0 left-0 rounded-full", BAR_FILL[band])} style={{ width: `${fill}%` }} />
        <div className="absolute -top-[3px] -bottom-[3px] w-[2px] rounded-full bg-ink-3" style={{ left: `${tick}%` }} />
      </div>
    </div>
  );
}

export function ComponentBar({ label, value, weight }: { label: string; value: number; weight?: number }) {
  return (
    <div className="min-w-0">
      <div className="mb-2 flex items-baseline justify-between gap-3 text-[13px]">
        <span className="truncate text-ink-2">{label}</span>
        <span className="num shrink-0 text-ink">
          {value.toFixed(2)}
          {weight !== undefined && <span className="text-ink-3"> × {weight.toFixed(2)}</span>}
        </span>
      </div>
      <div className="h-[5px] rounded-full bg-surface-3" aria-hidden="true">
        <div className="h-full rounded-full bg-teal" style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
      </div>
    </div>
  );
}

export function CheckRow({ passed, label, detail }: { passed: boolean | undefined; label: string; detail?: ReactNode }) {
  let icon = <CircleMinus size={17} className="text-ink-3" aria-hidden="true" />;
  let state = "Not evaluated";
  if (passed === true) {
    icon = <CircleCheck size={17} className="text-low" aria-hidden="true" />;
    state = "Passed";
  } else if (passed === false) {
    icon = <CircleX size={17} className="text-loss" aria-hidden="true" />;
    state = "Failed";
  }
  return (
    <li className="flex items-start gap-3 py-3">
      <span className="mt-[1px] shrink-0">{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[13.5px] text-ink">{label}</span>
        {detail && <span className="mt-0.5 block text-[12.5px] text-ink-3">{detail}</span>}
      </span>
      <span className={cx("shrink-0 text-[12px] font-semibold", passed === false ? "text-loss" : "text-ink-3")}>{state}</span>
    </li>
  );
}

export function KeyValue({ label, children, mono = false }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="flex min-w-0 items-baseline justify-between gap-4 py-2.5">
      <dt className="shrink-0 text-[13px] text-ink-3">{label}</dt>
      <dd className={cx("min-w-0 truncate text-right text-[13.5px] text-ink", mono && "num")}>{children}</dd>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("shimmer rounded-full", className)} aria-hidden="true" />;
}

export function LoadingBlock({ label = "Loading", rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3.5 py-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={`row-${index}`} className={cx("h-3.5", index % 3 === 2 ? "w-3/5" : index % 2 ? "w-4/5" : "w-full")} />
      ))}
    </div>
  );
}

export function EmptyState({ title, body, icon, action }: { title: string; body?: ReactNode; icon?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <span className="mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-surface-2 text-ink-3" aria-hidden="true">
        {icon ?? <Inbox size={18} />}
      </span>
      <p className="text-[15px] font-semibold text-ink">{title}</p>
      {body && <p className="max-w-md text-[13px] leading-relaxed text-ink-3">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry, compact = false }: { error: ApiError | Error; onRetry?: () => void; compact?: boolean }) {
  const unavailable = "kind" in error && (error as ApiError).kind === "unavailable";
  return (
    <div role="alert" className={cx("flex flex-col items-center justify-center gap-2 text-center", compact ? "px-4 py-8" : "px-6 py-14")}>
      <span className="mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-loss/12 text-loss" aria-hidden="true">
        {unavailable ? <ServerCrash size={18} /> : <TriangleAlert size={18} />}
      </span>
      <p className="text-[15px] font-semibold text-ink">{unavailable ? "Risk signal service unavailable" : "This view could not be loaded"}</p>
      <p className="max-w-lg text-[13px] leading-relaxed text-ink-2">{error.message}</p>
      {onRetry && (
        <button type="button" className="btn mt-3" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  );
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h3 className="text-[14px] font-semibold text-ink">{children}</h3>
      {aside && <span className="text-right text-[12.5px] text-ink-3">{aside}</span>}
    </div>
  );
}

export function Divider({ className }: { className?: string }) {
  return <hr className={cx("border-0 border-t border-line", className)} />;
}
