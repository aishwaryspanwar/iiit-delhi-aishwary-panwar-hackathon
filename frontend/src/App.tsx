import { useEffect } from "react";
import { AppProvider, useApp, type BootState } from "./state";
import { useRoute, type PageId } from "./lib/router";
import { useTheme } from "./lib/theme";
import { DetailDrawer } from "./components/Detail";
import { ReplayBar } from "./components/Replay";
import { BrandMark, PageHeader, TopNav } from "./components/Shell";
import { ErrorState, Skeleton } from "./components/ui";
import { Overview } from "./pages/Overview";
import { Signals } from "./pages/Signals";
import { Stress } from "./pages/Stress";
import { Headline } from "./pages/Headline";
import { System } from "./pages/System";

const PAGE_COPY: Record<PageId, { title: string; subtitle: string; replay: boolean }> = {
  overview: { title: "Dashboard", subtitle: "What is happening, how risky it is, what caused it, and what it could do to the book", replay: true },
  signals: { title: "Signal feed", subtitle: "Every news item and post, scored for event class, sentiment and impact", replay: true },
  stress: { title: "Portfolio stress test", subtitle: "Module B: event-triggered stress of a synthetic wholesale-banking book", replay: false },
  headline: { title: "Try a headline", subtitle: "Score your own text with the live rule engine and preview its stress impact", replay: false },
  system: { title: "Methodology", subtitle: "Data provenance, pipeline, trigger rules and scenario library", replay: false },
};

function Workspace() {
  const route = useRoute();
  const copy = PAGE_COPY[route.page];
  const { closeDetail } = useApp();
  useEffect(() => closeDetail(), [route.page, route.param, closeDetail]);
  useEffect(() => {
    document.title = `${copy.title} | Risk Engine`;
  }, [copy.title]);
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav page={route.page} />
      <div className="flex min-w-0 flex-1 flex-col">
        <PageHeader title={copy.title} subtitle={copy.subtitle}>
          {copy.replay ? <ReplayBar /> : null}
        </PageHeader>
        <main id="main" key={route.page} className="fade mx-auto w-full max-w-[1440px] flex-1 px-4 pb-10 md:px-8">
          {route.page === "overview" && <Overview />}
          {route.page === "signals" && <Signals />}
          {route.page === "stress" && <Stress selected={route.param} />}
          {route.page === "headline" && <Headline />}
          {route.page === "system" && <System />}
        </main>
        <footer className="mx-auto w-full max-w-[1440px] px-4 pb-8 text-[12.5px] text-ink-3 md:px-8">
          Historical replay of precomputed data on a synthetic portfolio. Not investment advice.
        </footer>
      </div>
      <DetailDrawer />
    </div>
  );
}

function BootScreen({ state }: { state: BootState }) {
  useTheme();
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="panel w-full max-w-lg p-8">
        <div className="mb-5 flex items-center gap-3">
          <BrandMark size={32} />
          <div>
            <div className="text-[17px] font-semibold text-ink">Risk Engine</div>
            <div className="text-[13px] text-ink-3">Event-driven risk signals and portfolio stress testing</div>
          </div>
        </div>
        {state.phase === "error" && state.error ? (
          <ErrorState error={state.error} onRetry={state.retry} compact />
        ) : (
          <div role="status" aria-live="polite" className="flex flex-col gap-2.5">
            <span className="text-[13.5px] text-ink-2">Loading precomputed signals and stress results</span>
            <Skeleton className="h-3" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider fallback={(state) => <BootScreen state={state} />}>
      <Workspace />
    </AppProvider>
  );
}
