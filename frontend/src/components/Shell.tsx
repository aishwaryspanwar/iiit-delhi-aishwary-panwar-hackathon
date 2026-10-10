import type { ReactNode } from "react";
import { Moon, Sun } from "lucide-react";
import { useApp } from "../state";
import { href, type PageId } from "../lib/router";
import { cx } from "./ui";

const NAV: { id: PageId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "signals", label: "Signal feed" },
  { id: "entities", label: "Companies" },
  { id: "stress", label: "Stress test" },
  { id: "evaluation", label: "Evaluation" },
  { id: "headline", label: "Try a headline" },
  { id: "system", label: "Methodology" },
];

export function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true">
      <rect x="0.5" y="0.5" width="35" height="35" rx="11" fill="var(--surface-2)" stroke="var(--glass-border)" />
      <path d="M8 24l6.5-7.5 5 4 8.5-10" fill="none" stroke="var(--teal)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="28" cy="10.5" r="3" fill="var(--accent)" />
    </svg>
  );
}

export function TopNav({ page }: { page: PageId }) {
  const { datasets, dataset, setDataset, theme, toggleTheme, summary } = useApp();
  return (
    <header className="sticky top-0 z-30 px-3 pt-3 md:px-6">
      <div className="glass-nav mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-3 rounded-[28px] px-3 py-2.5 md:px-4">
        <a href={href("overview")} className="flex shrink-0 items-center gap-2.5 pr-2">
          <BrandMark />
          <span className="font-display text-[18px] leading-none text-ink">Risk Engine</span>
        </a>
        <nav aria-label="Primary" className="order-3 -mx-1 flex w-full gap-1 overflow-x-auto px-1 lg:order-none lg:mx-auto lg:w-auto">
          <div className="flex gap-1 rounded-full p-1 lg:bg-surface-2">
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
        <div className="ml-auto flex min-w-0 items-center gap-2 lg:ml-0">
          <span className="hidden items-center gap-2 rounded-full bg-teal-soft px-3 py-1.5 text-[12px] font-semibold text-teal-ink xl:flex" title={`Build ${summary.build?.build_id ?? "n/a"}, config ${summary.build?.config_hash ?? "n/a"}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-teal" aria-hidden="true" />
            Offline replay
          </span>
          <label className="flex min-w-0 items-center">
            <span className="sr-only">Dataset</span>
            <select className="control w-full min-w-0 max-w-[340px] pr-9" value={dataset} onChange={(e) => setDataset(e.target.value)}>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
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

export function PageHeader({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 pt-8 pb-5 md:px-8">
      <h1 className="text-[34px] leading-[1.1] font-medium tracking-[-0.02em] text-ink md:text-[40px]">{title}</h1>
      <p className="mt-2 max-w-[80ch] text-[14.5px] text-ink-3">{subtitle}</p>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}
