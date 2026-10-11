import { useRef, type KeyboardEvent } from "react";
import { cx } from "./ui";

export interface SegmentOption<T extends string> {
  id: T;
  label: string;
  disabled?: boolean;
  hint?: string;
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  idPrefix,
  variant = "tabs",
  size = "md",
  bare = false,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  idPrefix: string;
  variant?: "tabs" | "radio";
  size?: "sm" | "md";
  bare?: boolean;
}) {
  const tabs = variant === "tabs";
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.map((option, index) => (option.disabled ? -1 : index)).filter((index) => index >= 0);
  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const position = enabled.indexOf(index);
    const last = enabled.length - 1;
    const target = {
      ArrowRight: enabled[position === last ? 0 : position + 1],
      ArrowDown: enabled[position === last ? 0 : position + 1],
      ArrowLeft: enabled[position <= 0 ? last : position - 1],
      ArrowUp: enabled[position <= 0 ? last : position - 1],
      Home: enabled[0],
      End: enabled[last],
    }[event.key];
    if (target === undefined) return;
    event.preventDefault();
    onChange(options[target].id);
    refs.current[target]?.focus();
  };
  return (
    <div role={tabs ? "tablist" : "radiogroup"} aria-label={label} className={cx("flex rounded-full", !bare && "border border-[var(--glass-border)] bg-surface-2 p-1")}>
      {options.map((option, index) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role={tabs ? "tab" : "radio"}
            id={`${idPrefix}-tab-${option.id}`}
            aria-selected={tabs ? selected : undefined}
            aria-checked={tabs ? undefined : selected}
            aria-controls={tabs ? `${idPrefix}-panel` : undefined}
            aria-disabled={option.disabled || undefined}
            title={option.hint}
            tabIndex={selected ? 0 : -1}
            onClick={() => !option.disabled && onChange(option.id)}
            onKeyDown={(event) => move(event, index)}
            className={cx(
              "rounded-full transition-colors duration-150",
              tabs ? "min-w-0 flex-1 truncate" : "shrink-0 whitespace-nowrap",
              size === "sm" ? "h-8 px-3.5 text-[13px]" : "h-8 px-3 text-[13.5px]",
              selected && !bare && "bg-accent font-semibold text-on-accent shadow-[0_8px_20px_-12px_var(--accent-glow)]",
              selected && bare && "bg-surface-3 font-semibold text-ink",
              !selected && "text-ink-2 hover:text-ink",
              option.disabled && "cursor-not-allowed opacity-45 hover:text-ink-2",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
