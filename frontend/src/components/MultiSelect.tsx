import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { cx } from "./ui";

export function MultiSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (option: string) => onChange(value.includes(option) ? value.filter((v) => v !== option) : [...value, option]);
  let summary = `${value.length} selected`;
  if (value.length === 0) summary = "All";
  else if (value.length === 1) summary = options.find((o) => o.value === value[0])?.label ?? value[0];

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        className={cx("control flex items-center gap-2 pr-2.5", value.length > 0 && "bg-teal-soft")}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={listId}
      >
        <span className="text-ink-3">{label}</span>
        <span className={cx("max-w-[150px] truncate", value.length > 0 ? "font-semibold text-teal-ink" : "text-ink")}>{summary}</span>
        <ChevronDown size={15} className={cx("text-ink-3 transition-transform duration-200", open && "rotate-180")} aria-hidden="true" />
      </button>
      {open && (
        <div id={listId} className="overlay fade absolute left-0 z-30 mt-2 w-64 rounded-2xl p-2" role="group" aria-label={label}>
          <ul className="max-h-72 overflow-y-auto">
            {options.map((option) => {
              const checked = value.includes(option.value);
              return (
                <li key={option.value}>
                  <label className="flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 text-[13.5px] text-ink hover:bg-surface-2">
                    <input type="checkbox" className="sr-only" checked={checked} onChange={() => toggle(option.value)} />
                    <span
                      className={cx("flex h-[18px] w-[18px] items-center justify-center rounded-[6px]", checked ? "bg-pill text-on-pill" : "bg-surface-3")}
                      aria-hidden="true"
                    >
                      {checked && <Check size={12} strokeWidth={3} />}
                    </span>
                    {option.label}
                  </label>
                </li>
              );
            })}
          </ul>
          {value.length > 0 && (
            <button type="button" className="mt-1 w-full rounded-lg px-2.5 py-2 text-left text-[13px] text-ink-3 hover:bg-surface-2 hover:text-ink" onClick={() => onChange([])}>
              Clear selection
            </button>
          )}
        </div>
      )}
    </div>
  );
}
