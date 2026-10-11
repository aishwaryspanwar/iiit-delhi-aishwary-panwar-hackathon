import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Check, ChevronDown } from "lucide-react";
import { cx } from "./ui";

export interface SelectOption<T> {
  value: T;
  label: string;
}

export function Select<T>({
  options,
  value,
  onChange,
  label,
  buttonClassName,
  menuClassName = "w-[200px]",
}: {
  options: SelectOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  buttonClassName?: string;
  menuClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const selectedIndex = Math.max(0, options.findIndex((o) => o.value === value));
  const [active, setActive] = useState(selectedIndex);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    setActive(selectedIndex);
    list.current?.focus();
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open, selectedIndex]);

  const close = (refocus: boolean) => {
    setOpen(false);
    if (refocus) button.current?.focus();
  };
  const choose = (index: number) => {
    onChange(options[index].value);
    close(true);
  };
  const onButtonKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
    }
  };
  const onListKey = (event: KeyboardEvent<HTMLUListElement>) => {
    const last = options.length - 1;
    if (event.key === "ArrowDown") setActive((i) => Math.min(last, i + 1));
    else if (event.key === "ArrowUp") setActive((i) => Math.max(0, i - 1));
    else if (event.key === "Home") setActive(0);
    else if (event.key === "End") setActive(last);
    else if (event.key === "Enter" || event.key === " ") choose(active);
    else if (event.key === "Escape") close(true);
    else if (event.key === "Tab") close(false);
    else return;
    if (event.key !== "Tab") event.preventDefault();
  };

  return (
    <div ref={root} className="relative shrink-0">
      <button
        ref={button}
        type="button"
        className={cx("control flex h-[34px] max-w-full items-center gap-2 pr-3 pl-3.5 text-[13px]", buttonClassName)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? `${id}-list` : undefined}
        aria-label={`${label}: ${options[selectedIndex]?.label}`}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onButtonKey}
      >
        <span className="min-w-0 truncate">{options[selectedIndex]?.label}</span>
        <ChevronDown size={14} aria-hidden="true" className={cx("shrink-0 text-ink-2 transition-transform duration-150", open && "rotate-180")} />
      </button>
      {open && (
        <ul
          ref={list}
          id={`${id}-list`}
          role="listbox"
          tabIndex={-1}
          aria-label={label}
          aria-activedescendant={`${id}-opt-${active}`}
          onKeyDown={onListKey}
          className={cx("absolute top-full right-0 z-40 mt-1.5 flex flex-col gap-0.5 rounded-2xl border border-[var(--glass-border)] bg-surface-solid p-1.5 shadow-pop outline-none", menuClassName)}
        >
          {options.map((option, index) => {
            const selected = index === selectedIndex;
            return (
              <li
                key={option.label}
                id={`${id}-opt-${index}`}
                role="option"
                aria-selected={selected}
                onPointerEnter={() => setActive(index)}
                onClick={() => choose(index)}
                className={cx(
                  "flex h-9 cursor-pointer items-center justify-between gap-3 rounded-[10px] px-3 text-[13px]",
                  selected ? "bg-accent-soft font-semibold text-accent-ink" : "text-ink-2",
                  index === active && !selected && "bg-surface-3 text-ink",
                )}
              >
                <span className="min-w-0 truncate">{option.label}</span>
                {selected && <Check size={14} aria-hidden="true" className="shrink-0 text-accent" />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
