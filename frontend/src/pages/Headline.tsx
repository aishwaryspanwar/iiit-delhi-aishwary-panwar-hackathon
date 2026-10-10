import { useState } from "react";
import { ArrowRight, CircleCheck, FlaskConical, ShieldAlert } from "lucide-react";
import { useApp } from "../state";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { integer, percent, score, usdMillions } from "../lib/format";
import { BAND_LABELS, SENTIMENT_TEXT, impactBand } from "../lib/risk";
import type { ScoreResult } from "../lib/types";
import { SignalExplain, TriggerChecks } from "../components/Detail";
import { BeforeAfter } from "../components/stress";
import { Divider, EmptyState, ErrorState, LoadingBlock, Panel, Stat, cx } from "../components/ui";

interface Submission {
  text: string;
  outlets: number;
  volume: number;
  preview: boolean;
}

function summarySentence(result: ScoreResult, className: (c: string) => string, threshold: number): string {
  const s = result.signal;
  const rules = s.event.matched_rules;
  const ruleWord = rules.length > 1 ? "rules" : "rule";
  const classPart =
    s.event.class === "other"
      ? "No taxonomy rule fired strongly enough, so the text is classed as Other"
      : `Classified as ${className(s.event.class)} (confidence ${s.event.confidence.toFixed(2)}) because ${ruleWord} ${rules.join(", ")} matched`;
  const band = BAND_LABELS[impactBand(s.impact.score, threshold)].toLowerCase();
  return `${classPart}. Sentiment is ${SENTIMENT_TEXT[s.sentiment.label].toLowerCase()} (${s.sentiment.score.toFixed(2)}). Item impact is ${score(s.impact.score)} out of 10, in the ${band} band.`;
}

export function Headline() {
  const { meta, summary, className } = useApp();
  const limits = meta.headline;
  const threshold = summary.trigger_settings.impact_threshold;
  const [text, setText] = useState("");
  const [submission, setSubmission] = useState<Submission | null>(null);

  const result = useAsync(
    submission
      ? (signal) => api.score({ text: submission.text, outlets: submission.outlets, volume_multiple: submission.volume, preview: submission.preview }, signal)
      : null,
    [submission?.text, submission?.outlets, submission?.volume, submission?.preview],
  );

  const submit = (value: string) => {
    if (!value.trim()) return;
    setSubmission((current) => ({ text: value, outlets: current?.outlets ?? limits.outlet_range[0], volume: current?.volume ?? limits.volume_options[0], preview: current?.preview ?? false }));
  };
  const onSubmit = (e: { preventDefault: () => void }) => {
    e.preventDefault();
    submit(text);
  };
  const update = (patch: Partial<Submission>) => setSubmission((current) => (current ? { ...current, ...patch } : current));
  const data = result.data;
  const outletFill = submission ? ((submission.outlets - limits.outlet_range[0]) / (limits.outlet_range[1] - limits.outlet_range[0])) * 100 : 0;
  const failedChecks = data ? Object.values(data.checks).filter((v) => !v).length : 0;

  return (
    <div className="grid grid-cols-12 items-start gap-5">
      <Panel className="col-span-12" title="Score your own headline or post" description="Analysis of your text with the same rule engine that scored the feed">
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label htmlFor="headline-input" className="sr-only">
            Headline or post
          </label>
          <div className="relative">
            <textarea
              id="headline-input"
              value={text}
              maxLength={limits.max_length}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(text);
                }
              }}
              rows={2}
              placeholder="Central bank unexpectedly raises rates by 75 basis points as inflation hits a 40-year high"
              className="control h-auto min-h-[88px] w-full resize-y rounded-2xl px-5 py-4 text-[17px] leading-snug"
            />
            <span className="num pointer-events-none absolute right-4 bottom-3 text-[12px] text-ink-3" aria-live="polite">
              {text.length} / {limits.max_length}
            </span>
          </div>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
              <span className="mr-1 text-[13px] text-ink-3">Try an example</span>
              {limits.examples.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setText(example);
                    submit(example);
                  }}
                  className="chip max-w-[320px]"
                  title={example}
                >
                  <span className="truncate">{example}</span>
                </button>
              ))}
            </div>
            <button type="submit" className="btn btn-primary h-10 px-5" disabled={!text.trim()}>
              <FlaskConical size={15} aria-hidden="true" /> Score this text
            </button>
          </div>
          <p className="text-[12.5px] leading-relaxed text-ink-3">
            Sentiment uses {limits.sentiment_model}. Nothing leaves this machine and nothing is stored; your text is treated as plain text. The precomputed feed may use a different
            sentiment model.
          </p>
        </form>
      </Panel>

      {!submission && (
        <Panel className="col-span-12">
          <EmptyState
            title="Enter a headline to score it"
            body="You will see its event class, sentiment, impact and the reasoning behind each, then test whether it would trigger a portfolio stress test."
            icon={<FlaskConical size={18} />}
          />
        </Panel>
      )}

      {submission && result.error && (
        <Panel className="col-span-12" title="This text could not be scored">
          <ErrorState error={result.error} onRetry={result.error.kind === "bad_request" ? undefined : result.reload} />
        </Panel>
      )}

      {submission && !result.error && !data && (
        <Panel className="col-span-12" title="Scoring">
          <LoadingBlock rows={5} label="Scoring headline" />
        </Panel>
      )}

      {submission && !result.error && data && (
        <>
          <Panel className={cx("col-span-12 transition-opacity xl:col-span-7", result.loading && "opacity-70")} title="How the engine read your text">
            <p className="mb-8 rounded-2xl bg-teal-soft px-5 py-4 text-[14px] leading-relaxed text-ink">{summarySentence(data, className, threshold)}</p>
            <SignalExplain signal={data.signal} />
          </Panel>

          <div className={cx("col-span-12 flex flex-col gap-5 transition-opacity xl:col-span-5", result.loading && "opacity-70")}>
            <Panel title="Would this trigger a stress test?" description="One item is never enough on its own. Set how widely the story is being reported.">
              <div className="flex flex-col gap-6">
                <label className="block">
                  <span className="mb-2 flex items-baseline justify-between text-[13.5px] text-ink-2">
                    Distinct news outlets reporting <span className="figure text-[17px] text-ink">{submission.outlets}</span>
                  </span>
                  <input
                    type="range"
                    className="range"
                    min={limits.outlet_range[0]}
                    max={limits.outlet_range[1]}
                    value={submission.outlets}
                    onChange={(e) => update({ outlets: Number(e.target.value) })}
                    style={{ ["--fill" as string]: `${outletFill}%` }}
                  />
                </label>
                <fieldset>
                  <legend className="mb-2.5 text-[13.5px] text-ink-2">Mentions compared with the topic's normal daily volume</legend>
                  <div className="flex flex-wrap gap-1.5">
                    {limits.volume_options.map((v) => (
                      <button key={v} type="button" aria-pressed={submission.volume === v} onClick={() => update({ volume: v })} className="chip num min-w-[48px] justify-center px-3">
                        {v}×
                      </button>
                    ))}
                  </div>
                </fieldset>
              </div>
              <Divider className="my-6" />
              <div className="grid grid-cols-2 gap-6">
                <Stat label="Event impact if reported this widely" value={`${score(data.event.impact)} / 10`} tone={impactBand(data.event.impact, threshold)} />
                <Stat
                  label="Decision"
                  value={data.triggered ? "Triggers" : "No trigger"}
                  tone={data.triggered ? "critical" : "default"}
                  sub={data.triggered ? "Every condition is met" : `${failedChecks} ${failedChecks === 1 ? "check fails" : "checks fail"}`}
                />
              </div>
              <div className="mt-4">
                <TriggerChecks event={data.event} checks={data.checks} settings={summary.trigger_settings} />
              </div>
            </Panel>

            <Panel
              title="Portfolio stress test preview"
              description="Module B on the synthetic book"
              actions={
                !data.triggered && (
                  <button type="button" className="chip" aria-pressed={submission.preview} onClick={() => update({ preview: !submission.preview })}>
                    Preview anyway
                  </button>
                )
              }
            >
              {data.triggered && (
                <p className="mb-5 flex items-center gap-2 text-[13.5px] font-medium text-low">
                  <CircleCheck size={16} aria-hidden="true" /> Every trigger condition is met, so this stress test would run automatically.
                </p>
              )}
              {!data.scenario_defined && (data.triggered || submission.preview) && (
                <EmptyState title={`No stress scenario is defined for ${className(data.event.class)} events`} icon={<ShieldAlert size={18} />} />
              )}
              {!data.run && data.scenario_defined && !data.triggered && !submission.preview && (
                <p className="flex items-center gap-2 text-[13.5px] text-ink-3">
                  Choose Preview anyway to run the {className(data.event.class)} scenario at this impact <ArrowRight size={14} aria-hidden="true" />
                </p>
              )}
              {data.run && (
                <div className="flex flex-col gap-6">
                  <BeforeAfter totals={data.run.totals} size="sm" />
                  <dl className="grid grid-cols-3 gap-4">
                    <div>
                      <dt className="caption">In scope</dt>
                      <dd className="figure mt-1.5 text-[19px] text-ink">{integer(data.run.in_scope_positions)}</dd>
                    </div>
                    <div>
                      <dt className="caption">Multiplier</dt>
                      <dd className="figure mt-1.5 text-[19px] text-ink">×{data.run.shocks_applied.multiplier.toFixed(2)}</dd>
                    </div>
                    <div>
                      <dt className="caption">Stress P&L</dt>
                      <dd className="figure mt-1.5 text-[19px] text-loss">{usdMillions(data.run.totals.pnl)}</dd>
                    </div>
                  </dl>
                  <p className="text-[13px] leading-relaxed text-ink-3">{data.run.explanation}</p>
                  <p className="text-[12.5px] text-ink-3">Preview on the synthetic book: {percent(data.run.totals.pnl_pct)} of portfolio value.</p>
                </div>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
