import { useEffect, useRef, type ReactNode } from "react";
import { ArrowRight, ExternalLink, X } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../state";
import { useAsync } from "../lib/useAsync";
import { dateTime, integer, safeHttpUrl, score, signed, usdMillions, percent } from "../lib/format";
import { CHECK_ORDER, SCOPE_TEXT, SENTIMENT_TEXT, SOURCE_TEXT, impactBand } from "../lib/risk";
import { href } from "../lib/router";
import type { CheckName, ClusterEvent, Decision, EventDetail, Meta, Signal, TriggerSettings } from "../lib/types";
import { BandBadge, CheckRow, ClassTag, ComponentBar, Divider, ErrorState, ImpactMeter, KeyValue, LoadingBlock, SectionTitle, SentimentValue, StatusBadge, cx } from "./ui";

const ESCAPE_PATTERN = /[.*+?^${}()|[\]\\]/g;

export function HighlightedText({ text, terms }: { text: string; terms: string[] }) {
  const unique = [...new Set(terms.filter((t) => t.length > 1))].sort((a, b) => b.length - a.length);
  if (!unique.length) return <>{text}</>;
  const pattern = new RegExp(`(${unique.map((t) => t.replace(ESCAPE_PATTERN, String.raw`\$&`)).join("|")})`, "gi");
  const pieces = text.split(pattern);
  let offset = 0;
  return (
    <>
      {pieces.map((piece, index) => {
        const key = `${offset}-${piece}`;
        offset += piece.length;
        return index % 2 === 1 ? (
          <mark key={key} className="rounded-[4px] bg-teal-soft px-1 text-inherit">
            {piece}
          </mark>
        ) : (
          <span key={key}>{piece}</span>
        );
      })}
    </>
  );
}

export function checkDetail(name: CheckName, event: ClusterEvent, settings: TriggerSettings, className: (c: string) => string): string {
  switch (name) {
    case "stress_class":
      return `${className(event.class)} ${settings.stress_classes.includes(event.class) ? "is" : "is not"} a stress-relevant class`;
    case "impact_above_threshold":
      return `Event impact ${score(event.impact)} against a threshold of ${settings.impact_threshold}`;
    case "confidence_ok":
      return `Mean confidence ${event.confidence_mean.toFixed(2)} against a minimum of ${settings.min_confidence}`;
    case "not_positive":
      return `Mean sentiment ${signed(event.sentiment_mean)} against a maximum of ${signed(settings.max_sentiment)}`;
    case "corroborated":
      return `${event.n_outlets} distinct outlets against a minimum of ${settings.min_news_outlets}`;
    case "baseline_ready":
      return event.warmup ? "Still inside the volume-baseline warm-up window" : "Volume baseline available";
    case "cooldown":
      return `Same class fired within ${settings.cooldown_hours} h without a ${settings.rearm_impact_delta}-point impact increase`;
  }
}

export function TriggerChecks({
  event,
  decision,
  checks,
  settings,
}: {
  event: ClusterEvent;
  decision?: Decision | null;
  checks?: Partial<Record<CheckName, boolean>>;
  settings: TriggerSettings;
}) {
  const { meta, className } = useApp();
  const values: Partial<Record<CheckName, boolean>> = { ...(decision?.checks ?? checks ?? {}) };
  if (decision) values.cooldown = !decision.failed.includes("cooldown");
  const names = CHECK_ORDER.filter((name) => name in values);
  return (
    <ul className="divide-y divide-line">
      {names.map((name) => (
        <CheckRow key={name} passed={values[name]} label={meta.check_labels[name]} detail={checkDetail(name, event, settings, className)} />
      ))}
    </ul>
  );
}

function RuleList({ rules, meta }: { rules: string[]; meta: Meta }) {
  if (!rules.length) return <p className="text-[13.5px] text-ink-3">No taxonomy rule matched, so the item falls back to Other.</p>;
  return (
    <ul className="flex flex-col gap-2">
      {rules.map((id) => {
        const rule = meta.rules[id];
        return (
          <li key={id} className="well px-4 py-3">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[13.5px]">
                <span className="flex items-center gap-3">
                  <span className="num font-semibold text-teal-ink">{id}</span>
                  {rule && <span className="text-ink-2">{meta.classes[rule.class]}</span>}
                </span>
                {rule && <span className="num text-[12.5px] text-ink-3">Weight {rule.weight.toFixed(1)}</span>}
              </summary>
              {rule && (
                <ul className="mt-3 flex flex-col gap-1.5 border-t border-line pt-3">
                  {rule.patterns.map((pattern) => (
                    <li key={pattern} className="num text-[12px] break-all text-ink-3">
                      {pattern}
                    </li>
                  ))}
                </ul>
              )}
            </details>
          </li>
        );
      })}
    </ul>
  );
}

const IMPACT_COMPONENT_TEXT: Record<string, string> = {
  class_prior: "Class prior",
  sentiment_mag: "Sentiment magnitude",
  entity_importance: "Entity importance",
  cue_bonus: "Severity cue words",
};

const CLUSTER_COMPONENT_TEXT: Record<string, string> = {
  severity: "Severity, top-3 items",
  breadth: "Breadth of outlets",
  abnormal_volume: "Abnormal volume",
};

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="caption mb-1.5 truncate">{label}</div>
      <div className="truncate text-[15px] font-semibold text-ink">{value}</div>
    </div>
  );
}

export function SignalExplain({ signal }: { signal: Signal }) {
  const { meta, summary, className, entityName } = useApp();
  const threshold = summary.trigger_settings.impact_threshold;
  const url = safeHttpUrl(signal.url);
  return (
    <div className="flex flex-col gap-8">
      <div>
        <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-3">
          <span className="font-semibold text-ink-2">{SOURCE_TEXT[signal.source] ?? signal.source}</span>
          {signal.outlet && <span>{signal.outlet}</span>}
          <span className="num">{dateTime(signal.published_at)}</span>
          {signal.duplicate_count > 1 && <span className="num">{signal.duplicate_count} duplicates merged</span>}
        </div>
        <p className="text-[19px] leading-snug font-medium text-ink">
          <HighlightedText text={signal.text ?? "(no text)"} terms={signal.entities.map((e) => e.matched)} />
        </p>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-medium text-teal-ink hover:underline">
            Read the original article <ExternalLink size={13} aria-hidden="true" />
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
        <Fact label="Event class" value={className(signal.event.class)} />
        <Fact label="Confidence" value={<span className="num">{signal.event.confidence.toFixed(2)}</span>} />
        <Fact label="Sentiment" value={<SentimentValue value={signal.sentiment.score} />} />
        <Fact
          label="Item impact"
          value={
            <span className="flex items-center gap-2">
              <span className="num">{score(signal.impact.score)}</span>
              <BandBadge band={impactBand(signal.impact.score, threshold)} />
            </span>
          }
        />
      </div>

      <section>
        <SectionTitle aside={signal.event.runner_up ? `Runner-up: ${className(signal.event.runner_up)}` : undefined}>Why this classification</SectionTitle>
        <RuleList rules={signal.event.matched_rules} meta={meta} />
      </section>

      <section>
        <SectionTitle aside={`1 + 9 × Σ weight × component, ${signal.impact.weights_version}`}>Why this impact score</SectionTitle>
        <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
          {Object.entries(signal.impact.components).map(([key, value]) => (
            <ComponentBar key={key} label={IMPACT_COMPONENT_TEXT[key] ?? key} value={value} weight={meta.impact_weights[key]} />
          ))}
        </div>
      </section>

      <section>
        <SectionTitle aside={SCOPE_TEXT[signal.scope]}>Entities and scope</SectionTitle>
        {signal.entities.length ? (
          <ul className="flex flex-wrap gap-2">
            {signal.entities.map((entity) => (
              <li key={entity.id} className="flex items-center gap-2 rounded-full bg-surface-2 px-3.5 py-1.5 text-[13px]">
                <span className="font-medium text-ink">{entity.name}</span>
                <span className="text-ink-3">{entity.type.replace("_", " ")}</span>
                {entity.ticker && <span className="num text-teal-ink">${entity.ticker}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13.5px] text-ink-3">No known entity was tagged in this item.</p>
        )}
        {signal.scope_targets.length > 0 && (
          <p className="mt-3 text-[13px] text-ink-3">
            Scope targets: <span className="text-ink-2">{signal.scope_targets.map((t) => entityName(t)).join(", ")}</span>
          </p>
        )}
      </section>

      <section>
        <SectionTitle>Provenance</SectionTitle>
        <dl className="well divide-y divide-line px-4 py-1">
          <KeyValue label="Signal ID" mono>{signal.signal_id}</KeyValue>
          <KeyValue label="Source record" mono>{signal.source_id}</KeyValue>
          <KeyValue label="Text hash" mono>{signal.text_hash.slice(0, 16)}…</KeyValue>
          <KeyValue label="Sentiment model" mono>{signal.sentiment.model}</KeyValue>
          <KeyValue label="Sentiment label">{SENTIMENT_TEXT[signal.sentiment.label]}</KeyValue>
          <KeyValue label="Build and config" mono>
            {signal.build.build_id}, {signal.build.config_hash}
          </KeyValue>
        </dl>
      </section>
    </div>
  );
}

export function ClusterExplain({ detail, compact = false }: { detail: EventDetail; compact?: boolean }) {
  const { meta, summary, className, openDetail } = useApp();
  const { event, decision, run } = detail;
  const settings = summary.trigger_settings;
  const failedCount = decision?.failed.length ?? 0;
  return (
    <div className="flex flex-col gap-8">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <ClassTag label={className(event.class)} emphasis={settings.stress_classes.includes(event.class)} />
          <StatusBadge status={event.status} />
          <BandBadge band={impactBand(event.impact, settings.impact_threshold)} />
          <span className="num ml-1 text-[13px] text-ink-3">{dateTime(event.t_start)}</span>
        </div>
        {!compact && event.lead?.text && (
          <p className="mt-4 text-[19px] leading-snug font-medium text-ink">
            “{event.lead.text}”
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
        <Fact label="Cluster impact" value={<span className="num">{score(event.impact)}</span>} />
        <Fact label="Items and outlets" value={<span className="num">{`${integer(event.n_items)} / ${integer(event.n_outlets)}`}</span>} />
        <Fact label="Mentions vs baseline" value={<span className="num">{`${integer(event.n_mentions)} / ${event.baseline_mentions.toFixed(1)}`}</span>} />
        <Fact label="Scope" value={SCOPE_TEXT[event.scope]} />
      </div>
      <p className="-mt-4 text-[13px] text-ink-3">
        Scope target: <span className="text-ink-2">{detail.scope_label}</span>
      </p>

      <section>
        <SectionTitle aside="Weighted cluster rubric">Why this cluster impact</SectionTitle>
        <div className="grid gap-x-8 gap-y-4 sm:grid-cols-3">
          {Object.entries(event.impact_components).map(([key, value]) => (
            <ComponentBar key={key} label={CLUSTER_COMPONENT_TEXT[key] ?? key} value={value} weight={meta.cluster_weights[key]} />
          ))}
        </div>
      </section>

      <section>
        <SectionTitle aside={event.status === "triggered" ? "All checks passed" : `${failedCount} failed`}>Stress-test trigger checks</SectionTitle>
        <TriggerChecks event={event} decision={decision} settings={settings} />
      </section>

      {run && (
        <a href={href("stress", run.cluster_id)} className="group flex items-center justify-between gap-4 rounded-2xl bg-loss/10 px-5 py-4 transition-shadow duration-200 hover:shadow-hover">
          <span>
            <span className="block text-[13px] font-medium text-loss">Stress test triggered</span>
            <span className="figure mt-1 block text-[24px] text-loss">
              {usdMillions(run.totals.pnl)}
              <span className="num ml-2 text-[13px] font-medium">{percent(run.totals.pnl_pct)} of portfolio</span>
            </span>
          </span>
          <span className="flex items-center gap-1.5 text-[13.5px] font-medium text-ink-2 group-hover:text-ink">
            Open stress test <ArrowRight size={15} className="transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </a>
      )}
      {!detail.scenario_defined && <p className="text-[13.5px] text-ink-3">No stress scenario is defined for {className(event.class)} events.</p>}

      <section>
        <SectionTitle aside={`${integer(detail.member_count)} items in cluster`}>Lead and member signals</SectionTitle>
        <ul className="-mx-3 flex flex-col">
          {detail.member_signals.slice(0, compact ? 6 : 12).map((s) => (
            <li key={s.signal_id}>
              <button
                type="button"
                onClick={() => openDetail({ kind: "signal", id: s.signal_id })}
                className={cx("flex w-full items-start gap-4 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-surface-2", event.representative_signal_ids.includes(s.signal_id) && "bg-teal-soft")}
              >
                <span className="w-28 shrink-0 pt-0.5">
                  <ImpactMeter value={s.impact.score} threshold={settings.impact_threshold} compact />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="line-clamp-2 text-[13.5px] text-ink">{s.text}</span>
                  <span className="text-[12px] text-ink-3">{s.outlet ?? SOURCE_TEXT[s.source]}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
      <p className="num text-[12px] break-all text-ink-3">Cluster {event.cluster_id}</p>
    </div>
  );
}

export function DetailDrawer() {
  const { detail, closeDetail, dataset } = useApp();
  const closeRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const state = useAsync<{ kind: "signal"; data: Awaited<ReturnType<typeof api.signal>> } | { kind: "event"; data: EventDetail }>(
    detail
      ? (signal) =>
          detail.kind === "signal"
            ? api.signal(dataset, detail.id, signal).then((data) => ({ kind: "signal" as const, data }))
            : api.event(dataset, detail.id, signal).then((data) => ({ kind: "event" as const, data }))
      : null,
    [detail?.kind, detail?.id, dataset],
  );

  useEffect(() => {
    if (!detail) return;
    returnFocus.current = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDetail();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      returnFocus.current?.focus?.();
    };
  }, [detail, closeDetail]);

  if (!detail) return null;
  const title = detail.kind === "signal" ? "Signal detail" : "Event cluster detail";
  const ready = state.data && state.data.kind === detail.kind && !state.loading;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <button type="button" className="fade absolute inset-0 cursor-default bg-black/45" aria-label="Close detail" onClick={closeDetail} tabIndex={-1} />
      <aside role="dialog" aria-modal="true" aria-labelledby="detail-title" className="overlay slide-in relative m-3 flex h-[calc(100%-1.5rem)] w-full max-w-[720px] flex-col rounded-3xl">
        <header className="flex items-center justify-between gap-4 px-8 pt-7 pb-5">
          <div>
            <h2 id="detail-title" className="font-display text-[20px] text-ink">
              {title}
            </h2>
            <p className="mt-0.5 text-[13px] text-ink-3">How the engine reached every number below</p>
          </div>
          <button ref={closeRef} type="button" className="btn icon-btn" onClick={closeDetail} aria-label="Close detail panel">
            <X size={16} aria-hidden="true" />
          </button>
        </header>
        <Divider />
        <div className="flex-1 overflow-y-auto px-8 py-7">
          {state.error && <ErrorState error={state.error} onRetry={state.reload} compact />}
          {!state.error && !ready && <LoadingBlock rows={8} label="Loading detail" />}
          {!state.error && ready && state.data?.kind === "signal" && (
            <div className="flex flex-col gap-10">
              <SignalExplain signal={state.data.data.signal} />
              {state.data.data.cluster ? (
                <section className="border-t border-line pt-8">
                  <h3 className="mb-5 text-[16px] font-semibold text-ink">The event cluster this signal belongs to</h3>
                  <ClusterExplain detail={state.data.data.cluster} compact />
                </section>
              ) : (
                <p className="text-[13.5px] text-ink-3">This signal is not part of an event cluster.</p>
              )}
            </div>
          )}
          {!state.error && ready && state.data?.kind === "event" && <ClusterExplain detail={state.data.data} />}
        </div>
      </aside>
    </div>
  );
}
