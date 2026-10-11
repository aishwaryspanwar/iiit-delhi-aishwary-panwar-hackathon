import { useRef, type ReactNode } from "react";
import { CircleHelp, Moon, Sun } from "lucide-react";
import { useApp } from "../state";
import { href, type PageId } from "../lib/router";
import { TIME_ZONE_LABEL, time } from "../lib/format";
import { Segmented, type SegmentOption } from "./Segmented";
import { Select } from "./Select";
import { cx } from "./ui";
import rippleMark from "../assets/ripple-mark.svg";

type Source = "offline" | "live";

const NAV: { id: PageId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "signals", label: "Signal feed" },
  { id: "stress", label: "Stress test" },
  { id: "headline", label: "Try a headline" },
];

export function BrandMark({ size = 36, className }: { size?: number; className?: string }) {
  const mask = `url("${rippleMark}") center / contain no-repeat`;
  return <span aria-hidden="true" className={cx("inline-block shrink-0 bg-ink", className)} style={{ width: size, height: size, mask, WebkitMask: mask }} />;
}

export function TopNav({ page, onTour }: { page: PageId; onTour: () => void }) {
  const { datasets, dataset, setDataset, theme, toggleTheme, summary, live } = useApp();
  const updated = summary.updated_at ? `${time(summary.updated_at)} ${TIME_ZONE_LABEL}` : "pending";
  const liveDataset = datasets.find((d) => d.live);
  const offline = datasets.filter((d) => !d.live);
  const lastOffline = useRef<string | undefined>(offline.find((d) => d.id === dataset)?.id ?? offline[0]?.id);
  if (!live && offline.some((d) => d.id === dataset)) lastOffline.current = dataset;
  const switchSource = (source: Source) => {
    if (source === "live" && liveDataset) setDataset(liveDataset.id);
    if (source === "offline" && lastOffline.current) setDataset(lastOffline.current);
  };
  const sources: SegmentOption<Source>[] = [
    { id: "offline", label: "Offline" },
    { id: "live", label: "Live", disabled: !liveDataset, hint: liveDataset ? undefined : "No live data yet: start it with python run.py --live" },
  ];
  return (
    <header className="sticky top-0 z-30 px-3 pt-3 md:px-6 3xl:px-8">
      <div className="glass-nav page-width mx-auto flex flex-wrap items-center gap-x-4 gap-y-3 rounded-[28px] px-3 py-2.5 md:px-4">
        <a href={href("overview")} className="flex shrink-0 items-center gap-2.5 pr-2">
          <BrandMark size={32} />
          <span className="font-display text-[19px] leading-none font-semibold tracking-[-0.01em] text-ink">Ripple</span>
        </a>
        <nav aria-label="Primary" className="order-3 -mx-1 flex w-full justify-center gap-1 overflow-x-auto px-1 xl:order-none xl:mx-auto xl:w-auto">
          <div data-tour="nav" className="flex gap-1 rounded-full bg-surface-2 p-1">
            {NAV.map((item) => (
              <a
                key={item.id}
                href={href(item.id)}
                aria-current={item.id === page ? "page" : undefined}
                className={cx(
                  "flex h-9 shrink-0 items-center rounded-full px-4 text-[13.5px] whitespace-nowrap transition-colors duration-150",
                  item.id === page ? "bg-pill font-semibold text-on-pill shadow-hover" : "text-ink-2 hover:bg-surface-3 hover:text-ink",
                )}
              >
                {item.label}
              </a>
            ))}
          </div>
        </nav>
        <div className="ml-auto flex min-w-0 items-center gap-2 xl:ml-0">
          <div data-tour="source" className="flex min-w-0 items-center gap-2 rounded-full">
            <Segmented options={sources} value={live ? "live" : "offline"} onChange={switchSource} label="Data source" idPrefix="source" variant="radio" size="sm" />
            {live ? (
              <span
                className="flex h-10 items-center gap-2 rounded-full bg-teal-soft px-3.5 text-[12.5px] font-semibold whitespace-nowrap text-teal-ink"
                title={`Build ${summary.build?.build_id ?? "n/a"}, config ${summary.build?.config_hash ?? "n/a"}`}
              >
                <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-teal" aria-hidden="true" />
                Updated {updated}
              </span>
            ) : (
              <Select
                options={offline.map((d) => ({ value: d.id, label: d.label }))}
                value={dataset}
                onChange={setDataset}
                label="Dataset"
                buttonClassName="h-10 w-[240px] justify-between 2xl:w-[300px]"
                menuClassName="w-[340px]"
              />
            )}
          </div>
          <button type="button" data-tour="help" className="btn icon-btn shrink-0" onClick={onTour} aria-label="Take the tour" title="Take the tour">
            <CircleHelp size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="btn icon-btn shrink-0"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            title={theme === "dark" ? "Light theme" : "Dark theme"}
          >
            {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
          </button>
        </div>
      </div>
    </header>
  );
}

export function PageHeader({ title, subtitle, centered = false, children }: { title: string; subtitle?: string; centered?: boolean; children?: ReactNode }) {
  return (
    <div className={cx("page-width mx-auto w-full px-4 pt-8 pb-5 md:px-8 3xl:px-10 short:pt-5 short:pb-4", centered && "pb-7 text-center short:pb-5")}>
      <h1 className="text-[34px] leading-[1.1] font-semibold tracking-[-0.02em] text-ink md:text-[40px] short:text-[32px]">{title}</h1>
      {subtitle && <p className={cx("mt-2 max-w-[80ch] text-[14.5px] text-ink-3", centered && "mx-auto")}>{subtitle}</p>}
      {children && <div className="mt-6 short:mt-4">{children}</div>}
    </div>
  );
}
