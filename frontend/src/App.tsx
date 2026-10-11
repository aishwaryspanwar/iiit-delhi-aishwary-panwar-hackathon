import { useEffect } from "react";
import { AppProvider, useApp, type BootState } from "./state";
import { useRoute, type PageId } from "./lib/router";
import { useTheme } from "./lib/theme";
import { DetailDrawer } from "./components/Detail";
import { ReplayBar } from "./components/Replay";
import { BrandMark, PageHeader, TopNav } from "./components/Shell";
import { Tour, useTour } from "./components/Tour";
import { ErrorState } from "./components/ui";
import { PageSkeleton } from "./components/Skeletons";
import { Overview } from "./pages/Overview";
import { Signals } from "./pages/Signals";
import { Stress } from "./pages/Stress";
import { Headline } from "./pages/Headline";

const PAGE_COPY: Record<PageId, { title: string; subtitle?: string; replay: boolean; centered?: boolean }> = {
  overview: { title: "Dashboard", replay: true },
  signals: { title: "Signal feed", replay: true },
  stress: { title: "Portfolio stress test", subtitle: "What a major news event would do to a synthetic bank portfolio", replay: false },
  headline: { title: "Try a headline", replay: false },
};

function Workspace() {
  const route = useRoute();
  const copy = PAGE_COPY[route.page];
  const { closeDetail } = useApp();
  const tour = useTour();
  useEffect(() => closeDetail(), [route.page, route.param, closeDetail]);
  useEffect(() => {
    if (tour.open) closeDetail();
  }, [tour.open, closeDetail]);
  useEffect(() => {
    document.title = `Ripple · ${copy.title}`;
  }, [copy.title]);
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav page={route.page} onTour={tour.start} />
      <div className="flex min-w-0 flex-1 flex-col">
        <PageHeader title={copy.title} subtitle={copy.subtitle} centered={copy.centered}>
          {copy.replay ? <ReplayBar /> : null}
        </PageHeader>
        <main id="main" key={route.page} className="fade page-width mx-auto w-full flex-1 px-4 pb-10 md:px-8 3xl:px-10">
          {route.page === "overview" && <Overview />}
          {route.page === "signals" && <Signals />}
          {route.page === "stress" && <Stress selected={route.param} />}
          {route.page === "headline" && <Headline />}
        </main>
        <footer className="page-width mx-auto w-full px-4 pb-8 text-[12.5px] text-ink-3 md:px-8 3xl:px-10">
          Historical replay of precomputed data on a synthetic portfolio. Not investment advice.
        </footer>
      </div>
      <DetailDrawer />
      {tour.open && <Tour onClose={tour.finish} />}
    </div>
  );
}

function BootScreen({ state }: { state: BootState }) {
  useTheme();
  const route = useRoute();
  const copy = PAGE_COPY[route.page];
  if (state.phase !== "error" || !state.error) return <PageSkeleton page={route.page} title={copy.title} subtitle={copy.subtitle} replay={copy.replay} />;
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="panel w-full max-w-lg p-8">
        <div className="mb-5 flex items-center gap-3">
          <BrandMark size={32} />
          <div className="text-[17px] font-semibold text-ink">Ripple</div>
        </div>
        <ErrorState error={state.error} onRetry={state.retry} compact />
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
