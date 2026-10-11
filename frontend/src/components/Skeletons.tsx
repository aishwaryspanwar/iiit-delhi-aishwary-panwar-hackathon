import type { CSSProperties, ReactNode } from "react";
import type { PageId } from "../lib/router";
import { BrandMark, PageHeader } from "./Shell";
import { cx } from "./ui";

export function Bone({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div className={cx("shimmer", className)} style={style} aria-hidden="true" />;
}

function Line({ className }: { className?: string }) {
  return <Bone className={cx("h-3 rounded-full", className)} />;
}

function SkPanel({ className, description = true, actions = false, children, bodyClassName }: { className?: string; description?: boolean; actions?: boolean; children: ReactNode; bodyClassName?: string }) {
  return (
    <div className={cx("panel flex min-w-0 flex-col", className)} aria-hidden="true">
      <div className="flex items-start justify-between gap-4 px-5 pt-5 md:px-6">
        <div className="flex min-w-0 flex-1 flex-col gap-2.5 pt-1">
          <Line className="h-3.5 w-44" />
          {description && <Line className="w-72 max-w-full" />}
        </div>
        {actions && <Bone className="h-9 w-28 rounded-full" />}
      </div>
      <div className={cx("min-w-0 flex-1 px-5 pt-5 pb-6 md:px-6", bodyClassName)}>{children}</div>
    </div>
  );
}

function ListRows({ rows, score = true }: { rows: number; score?: boolean }) {
  return (
    <div className="flex flex-col">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-start gap-4 px-3 py-3.5">
          <div className="flex min-w-0 flex-1 flex-col gap-2.5">
            <Line className={cx("h-3.5", i % 3 === 0 ? "w-4/5" : i % 3 === 1 ? "w-3/5" : "w-2/3")} />
            <div className="flex gap-2.5">
              <Line className="w-28" />
              <Bone className="h-[22px] w-24 rounded-full" />
              <Line className="w-20" />
            </div>
          </div>
          {score && (
            <div className="flex shrink-0 flex-col items-end gap-2">
              <Line className="h-4 w-9" />
              <Line className="w-14" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function CausalChainSkeleton() {
  return (
    <div className="@container" aria-hidden="true">
      <div className="grid grid-cols-1 gap-3 @lg:grid-cols-2 @3xl:grid-cols-3 @5xl:grid-cols-6">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="flex flex-col gap-3 rounded-2xl bg-surface-2 p-4">
          <div className="flex items-center gap-2">
            <Bone className="h-5 w-5 rounded-full" />
            <Line className="w-20" />
          </div>
          <Line className="h-3.5 w-3/4" />
          <Line className="w-full" />
          <Line className="w-1/2" />
        </div>
      ))}
      </div>
    </div>
  );
}

function BeforeAfterSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-6" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex flex-col gap-3">
          <Line className="w-20" />
          <Line className="h-7 w-32 max-w-full" />
        </div>
      ))}
    </div>
  );
}

function NavSkeleton({ page }: { page: PageId }) {
  const tabs: { id: PageId; width: string }[] = [
    { id: "overview", width: "w-[92px]" },
    { id: "signals", width: "w-[100px]" },
    { id: "stress", width: "w-[92px]" },
    { id: "headline", width: "w-[118px]" },
  ];
  return (
    <header className="sticky top-0 z-30 px-3 pt-3 md:px-6 3xl:px-8" aria-hidden="true">
      <div className="glass-nav page-width mx-auto flex flex-wrap items-center gap-2 rounded-[28px] p-2 xl:grid xl:grid-cols-[1fr_auto_1fr]">
        <div className="flex h-10 shrink-0 items-center gap-2.5 justify-self-start pr-3 pl-2">
          <BrandMark size={28} />
          <span className="font-display text-[18px] leading-none font-semibold tracking-[-0.01em] text-ink">Ripple</span>
        </div>
        <div className="order-3 flex w-full justify-center xl:order-none xl:w-auto">
          <div className="flex h-10 items-center gap-0.5 rounded-full bg-surface-2 p-1">
            {tabs.map((tab) => (
              <div key={tab.id} className={cx("h-8 rounded-full", tab.width, tab.id === page ? "bg-surface-3" : "")} />
            ))}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 justify-self-end xl:ml-0">
          <Bone className="h-10 w-[372px] rounded-full 2xl:w-[432px]" />
          <Bone className="h-10 w-[76px] rounded-full" />
        </div>
      </div>
    </header>
  );
}

function ReplaySkeleton() {
  return (
    <div className="panel flex flex-wrap items-center gap-x-6 gap-y-3 rounded-[28px] px-4 py-3 md:px-5" aria-hidden="true">
      <div className="flex items-center gap-1.5">
        <Bone className="h-10 w-10 rounded-full" />
        <Bone className="h-11 w-11 rounded-full" />
        <Bone className="h-10 w-10 rounded-full" />
      </div>
      <div className="flex min-w-[170px] flex-col gap-2.5">
        <Line className="w-20" />
        <Line className="h-4 w-36" />
      </div>
      <div className="flex min-w-[220px] flex-1 flex-col gap-3 pt-3">
        <Bone className="h-1 w-full rounded-full" />
        <div className="flex justify-between">
          <Line className="w-12" />
          <Line className="w-12" />
        </div>
      </div>
      <div className="hidden flex-col items-end gap-2.5 xl:flex">
        <Line className="w-16" />
        <Line className="h-3.5 w-24" />
      </div>
    </div>
  );
}

const DOT_GRID: CSSProperties = {
  backgroundImage: "radial-gradient(circle, var(--surface-3) 3.2px, transparent 3.8px)",
  backgroundSize: "26px 25.6px",
  backgroundPosition: "center top",
};

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-5">
      <div className="panel col-span-12 flex min-w-0 flex-col" aria-hidden="true">
        <div className="flex flex-col gap-2.5 px-5 pt-6 md:px-6">
          <Line className="h-3.5 w-36" />
          <Line className="w-80 max-w-full" />
        </div>
        <div className="grid min-w-0 gap-5 px-5 pt-5 md:px-6 xl:grid-cols-[minmax(0,1fr)_minmax(340px,394px)] 3xl:grid-cols-[minmax(0,1fr)_minmax(400px,460px)]">
          <Bone className="aspect-[2/1] w-full rounded-2xl" />
          <div className="flex min-h-[380px] flex-col gap-4 rounded-2xl bg-surface-2 p-4 xl:min-h-0">
            <Bone className="h-10 w-full rounded-full" />
            <div className="flex items-center justify-between">
              <Line className="w-40" />
              <Bone className="h-[22px] w-20 rounded-full" />
            </div>
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <div className="h-[72px] w-36 rounded-t-full border-[12px] border-b-0 border-[var(--surface-3)]" />
              <Line className="h-5 w-40" />
              <Line className="w-56" />
            </div>
            <Bone className="h-1.5 w-full rounded-full" />
          </div>
        </div>
        <div className="flex flex-wrap gap-5 px-5 pt-4 pb-6 md:px-6">
          {["w-16", "w-14", "w-16", "w-24"].map((w, i) => (
            <Line key={i} className={w} />
          ))}
        </div>
      </div>

      <SkPanel className="col-span-12" actions>
        <div className="mb-6 flex flex-wrap gap-6">
          <Line className="w-32" />
          <Line className="w-40" />
          <Line className="w-36" />
          <Line className="w-32" />
        </div>
        <div className="flex gap-4">
          <div className="flex w-[22px] flex-col justify-between py-1">
            {[0, 1, 2, 3].map((i) => (
              <Line key={i} className="w-3" />
            ))}
          </div>
          <div className="h-[256px] flex-1 rounded-lg" style={DOT_GRID} aria-hidden="true" />
          <div className="w-14" />
        </div>
      </SkPanel>

      <SkPanel className="col-span-12" bodyClassName="px-3 pt-2 pb-3">
        <ListRows rows={4} />
      </SkPanel>

      <SkPanel className="col-span-12 lg:col-span-7" description={false} actions bodyClassName="px-3 pt-2 pb-3">
        <ListRows rows={5} />
      </SkPanel>

      <SkPanel className="col-span-12 lg:col-span-5" description={false}>
        <div className="flex flex-col gap-5">
          {Array.from({ length: 7 }, (_, i) => (
            <div key={i} className="flex flex-col gap-2.5">
              <div className="flex justify-between">
                <Line className="w-28" />
                <Line className="w-10" />
              </div>
              <Bone className="h-[5px] rounded-full" style={{ width: `${92 - i * 12}%` }} />
            </div>
          ))}
        </div>
      </SkPanel>

      <SkPanel className="col-span-12" description={false}>
        <div className="flex flex-col gap-8">
          <CausalChainSkeleton />
          <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
            <BeforeAfterSkeleton />
            <Bone className="h-14 w-[300px] rounded-full" />
          </div>
        </div>
      </SkPanel>

      <SkPanel className="col-span-12" description={false}>
        <div className="grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="flex flex-col gap-4">
            <Bone className="h-3 w-full rounded-full" />
            <div className="flex gap-6">
              <Line className="w-20" />
              <Line className="w-20" />
              <Line className="w-20" />
            </div>
          </div>
          <Bone className="h-[180px] w-full rounded-xl" />
        </div>
      </SkPanel>
    </div>
  );
}

const SIGNAL_COLUMNS = "grid grid-cols-[112px_160px_minmax(0,1fr)_160px_120px_190px] gap-5 px-3";

export function SignalRowsSkeleton({ rows = 10 }: { rows?: number }) {
  return (
    <div className="overflow-hidden px-3" aria-hidden="true">
      <div className="min-w-[940px]">
        <div className={cx(SIGNAL_COLUMNS, "border-b border-line py-3.5")}>
          {["w-16", "w-14", "w-28", "w-20", "w-16", "w-14"].map((w, i) => (
            <Line key={i} className={w} />
          ))}
        </div>
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className={cx(SIGNAL_COLUMNS, "border-b border-line py-4 last:border-b-0")}>
            <div className="flex flex-col gap-2">
              <Line className="w-14" />
              <Line className="w-10" />
            </div>
            <div className="flex flex-col gap-2">
              <Line className="w-28" />
              <Line className="w-20" />
            </div>
            <div className="flex flex-col gap-2">
              <Line className={cx("h-3.5", i % 2 ? "w-3/4" : "w-11/12")} />
              {i % 3 === 0 && <Line className="h-3.5 w-1/2" />}
            </div>
            <Bone className="h-[22px] w-24 rounded-full" />
            <Line className="w-20" />
            <div className="flex items-center gap-3">
              <Line className="h-3.5 w-7" />
              <Bone className="h-[5px] flex-1 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SignalsSkeleton() {
  return (
    <div className="panel" aria-hidden="true">
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 pt-6">
        <Line className="h-3.5 w-52" />
        <div className="flex gap-1.5">
          <Bone className="h-[34px] w-36 rounded-full" />
          <Bone className="h-[34px] w-28 rounded-full" />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2.5 px-6 pt-5 pb-4">
        <Bone className="h-10 min-w-[240px] flex-1 rounded-full" />
        {["w-[104px]", "w-[112px]", "w-[132px]", "w-[156px]", "w-[170px]"].map((w) => (
          <Bone key={w} className={cx("h-10 rounded-full", w)} />
        ))}
      </div>
      <div className="border-t border-line" />
      <SignalRowsSkeleton />
      <div className="h-3" />
    </div>
  );
}

export function StressMainSkeleton() {
  return (
    <div className="flex min-w-0 flex-col gap-5" aria-hidden="true">
      <SkPanel description={false} actions>
        <CausalChainSkeleton />
      </SkPanel>
      <div className="panel grid grid-cols-12">
        <div className="col-span-12 flex flex-col gap-6 px-7 py-6 lg:col-span-8">
          <Line className="h-3.5 w-64" />
          <BeforeAfterSkeleton />
          <Line className="w-80 max-w-full" />
        </div>
        <div className="col-span-12 grid grid-cols-2 border-t border-line lg:col-span-4 lg:grid-cols-1 lg:border-t-0 lg:border-l">
          {[0, 1].map((i) => (
            <div key={i} className={cx("flex flex-col gap-3 px-7 py-6", i === 1 && "border-l border-line lg:border-t lg:border-l-0")}>
              <Line className="w-24" />
              <Line className="h-6 w-16" />
              <Line className="w-36" />
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-12 gap-5">
        {[0, 1].map((i) => (
          <SkPanel key={i} className="col-span-12 xl:col-span-6" description={i === 1}>
            <Bone className="h-[230px] w-full rounded-xl" />
          </SkPanel>
        ))}
      </div>
      <SkPanel description={false}>
        <div className="flex flex-col">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="grid grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,1fr))] gap-6 border-b border-line py-4 last:border-b-0">
              <Line className="w-24" />
              <Line className="ml-auto w-16" />
              <Line className="ml-auto w-16" />
              <Bone className="my-auto h-1 w-full rounded-full" />
              <Line className="ml-auto w-14" />
            </div>
          ))}
        </div>
      </SkPanel>
    </div>
  );
}

function StressSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-5">
      <div className="col-span-12 flex flex-col gap-5 xl:col-span-3" aria-hidden="true">
        <SkPanel description={false} bodyClassName="px-3 pt-3 pb-3">
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="flex flex-col gap-3 rounded-2xl bg-surface-2 p-4">
                <div className="flex justify-between">
                  <Line className="w-20" />
                  <Line className="w-14" />
                </div>
                <div className="flex gap-2">
                  <Bone className="h-[22px] w-24 rounded-full" />
                  <Line className="w-16" />
                </div>
                <Line className="w-full" />
              </div>
            ))}
          </div>
        </SkPanel>
        <SkPanel description={false}>
          <div className="mb-6 grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex flex-col gap-2.5">
                <Line className="w-14" />
                <Line className="h-5 w-12" />
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-5">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="flex flex-col gap-2.5">
                <div className="flex justify-between">
                  <Line className="w-32" />
                  <Line className="w-8" />
                </div>
                <Bone className="h-[5px] rounded-full" style={{ width: `${88 - i * 14}%` }} />
              </div>
            ))}
          </div>
        </SkPanel>
      </div>
      <div className="col-span-12 xl:col-span-9">
        <StressMainSkeleton />
      </div>
    </div>
  );
}

function HeadlineSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-5">
      <div className="panel col-span-12 px-6 pt-9 pb-8 md:px-12 md:pt-11 md:pb-10" aria-hidden="true">
        <div className="flex flex-col items-center gap-3">
          <Line className="h-6 w-80 max-w-full" />
          <Line className="w-96 max-w-full" />
        </div>
        <Bone className="mt-8 h-[152px] w-full rounded-[24px]" />
        <div className="mt-7 flex flex-col items-center gap-3">
          <Line className="w-28" />
          <div className="flex flex-wrap justify-center gap-2">
            {["w-64", "w-60", "w-64", "w-60", "w-52", "w-60"].map((w, i) => (
              <Bone key={i} className={cx("h-[34px] rounded-full", w)} />
            ))}
          </div>
        </div>
        <div className="mx-auto mt-8 max-w-[72ch] border-t border-line pt-5">
          <Line className="mx-auto w-56" />
        </div>
      </div>
    </div>
  );
}

const PAGE_SKELETON: Record<PageId, () => ReactNode> = {
  overview: OverviewSkeleton,
  signals: SignalsSkeleton,
  stress: StressSkeleton,
  headline: HeadlineSkeleton,
};

export function PageSkeleton({ page, title, subtitle, replay }: { page: PageId; title: string; subtitle?: string; replay: boolean }) {
  const Body = PAGE_SKELETON[page];
  return (
    <div className="flex min-h-screen flex-col" role="status" aria-live="polite">
      <span className="sr-only">Loading {title}</span>
      <NavSkeleton page={page} />
      <div aria-hidden="true">
        <PageHeader title={title} subtitle={subtitle}>
          {replay ? <ReplaySkeleton /> : null}
        </PageHeader>
      </div>
      <div className="page-width mx-auto w-full flex-1 px-4 pb-10 md:px-8 3xl:px-10">
        <Body />
      </div>
    </div>
  );
}
