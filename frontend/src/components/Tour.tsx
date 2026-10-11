import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { navigate, parseHash } from "../lib/router";
import { BrandMark } from "./Shell";
import { cx } from "./ui";

export const TOUR_STORAGE_KEY = "risk-engine-tour";

interface TourStep {
  target?: string;
  scroll?: boolean;
  title: string;
  body: string;
}

const STEPS: TourStep[] = [
  {
    title: "Welcome to Ripple",
    body: "Ripple reads news headlines and social posts, scores how risky each one is, and shows what a big event could do to a bank's portfolio. This short tour takes about a minute.",
  },
  {
    target: "nav",
    scroll: false,
    title: "Four pages",
    body: "Overview is the big picture. Signal feed lists every scored headline. Stress test shows the hit to the portfolio. Try a headline lets you score your own text.",
  },
  {
    target: "source",
    scroll: false,
    title: "Choose your data",
    body: "Offline replays a saved window of past news. Live follows fresh headlines and updates every 15 minutes.",
  },
  {
    target: "replay",
    title: "Replay the news",
    body: "Press play to watch the news unfold one day at a time. Every chart on the page follows this date. Red diamonds mark days when a stress test fired.",
  },
  {
    target: "map",
    title: "Where the news is, and how risky it is",
    body: "Bubbles show which countries the news is about; red means mostly negative news. The gauge shows the current risk level, from Low to Critical.",
  },
  {
    target: "timeline",
    title: "How risky each day was",
    body: "Related headlines are grouped into events and scored from 1 to 10. Each column lights up to the riskiest event in that period. Dots above the dashed line can trigger a stress test; red ones did.",
  },
  {
    target: "help",
    scroll: false,
    title: "You're all set",
    body: "Click any headline or event to see exactly how it was scored. You can replay this tour any time from this button.",
  },
];

const PAD = 8;
const GAP = 14;
const EDGE = 16;
const CARD_WIDTH = 360;
const WELCOME_WIDTH = 440;

interface Spot {
  top: number;
  left: number;
  width: number;
  height: number;
  radius: number;
}

function readDone(): boolean {
  try {
    return window.localStorage.getItem(TOUR_STORAGE_KEY) === "done";
  } catch {
    return false;
  }
}

function rememberDone(): void {
  try {
    window.localStorage.setItem(TOUR_STORAGE_KEY, "done");
  } catch {
    return;
  }
}

export function useTour(): { open: boolean; start: () => void; finish: () => void } {
  const [open, setOpen] = useState(() => !readDone());
  const start = useCallback(() => setOpen(true), []);
  const finish = useCallback(() => {
    rememberDone();
    setOpen(false);
  }, []);
  return { open, start, finish };
}

function measure(el: HTMLElement): Spot {
  const box = el.getBoundingClientRect();
  const radius = Number.parseFloat(getComputedStyle(el).borderTopLeftRadius) || 16;
  return { top: box.top - PAD, left: box.left - PAD, width: box.width + PAD * 2, height: box.height + PAD * 2, radius: Math.min(radius + PAD, 40) };
}

function placeCard(spot: Spot, width: number, height: number): CSSProperties {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const below = spot.top + spot.height + GAP;
  const above = spot.top - GAP - height;
  const wide = spot.width > width * 2;
  let left = wide ? spot.left + PAD + 16 : spot.left + spot.width / 2 - width / 2;
  let top: number;
  if (below + height <= vh - EDGE) top = below;
  else if (above >= EDGE) top = above;
  else {
    top = vh - height - EDGE;
    left = spot.left + PAD + 24;
  }
  left = Math.min(Math.max(left, EDGE), vw - width - EDGE);
  return { top, left, width };
}

export function Tour({ onClose }: { onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const [spot, setSpot] = useState<Spot | null>(null);
  const [cardHeight, setCardHeight] = useState(220);
  const card = useRef<HTMLDivElement>(null);
  const primary = useRef<HTMLButtonElement>(null);
  const step = STEPS[index];
  const welcome = index === 0;
  const last = index === STEPS.length - 1;

  const go = useCallback((next: number) => {
    if (next >= 1 && parseHash(window.location.hash).page !== "overview") navigate("overview");
    setIndex(Math.min(Math.max(next, 0), STEPS.length - 1));
  }, []);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    return () => previous?.focus?.({ preventScroll: true });
  }, []);

  useEffect(() => {
    if (!step.target) {
      setSpot(null);
      return;
    }
    let frame = 0;
    let target: HTMLElement | null = null;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        target = target?.isConnected ? target : document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
        setSpot(target ? measure(target) : null);
      });
    };
    const start = window.setTimeout(() => {
      target = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (target && step.scroll !== false) {
        const tall = target.getBoundingClientRect().height > window.innerHeight * 0.6;
        const smooth = !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
        target.scrollIntoView?.({ block: tall ? "start" : "center", behavior: smooth ? "smooth" : "auto" });
      }
      update();
    }, 30);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.clearTimeout(start);
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [step]);

  useLayoutEffect(() => {
    const height = card.current?.offsetHeight;
    if (height && height !== cardHeight) setCardHeight(height);
  });

  useEffect(() => {
    primary.current?.focus({ preventScroll: true });
  }, [index]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        if (last) onClose();
        else go(index + 1);
      } else if (event.key === "ArrowLeft" && index > 0) {
        event.preventDefault();
        go(index - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, last, go, onClose]);

  const trapFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab" || !card.current) return;
    const items = Array.from(card.current.querySelectorAll<HTMLElement>("button:not(:disabled)"));
    if (!items.length) return;
    const first = items[0];
    const end = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      end.focus();
    } else if (!event.shiftKey && document.activeElement === end) {
      event.preventDefault();
      first.focus();
    }
  };

  const width = Math.min(welcome ? WELCOME_WIDTH : CARD_WIDTH, window.innerWidth - EDGE * 2);
  const anchored = Boolean(step.target && spot);
  const cardStyle: CSSProperties = anchored && spot ? placeCard(spot, width, cardHeight) : { width };

  return (
    <div className="fixed inset-0 z-[70]" role="presentation">
      {anchored && spot ? (
        <div
          aria-hidden="true"
          className="pointer-events-none fixed transition-[top,left,width,height,border-radius] duration-300 ease-out"
          style={{
            top: spot.top,
            left: spot.left,
            width: spot.width,
            height: spot.height,
            borderRadius: spot.radius,
            boxShadow: "0 0 0 2px var(--accent), 0 0 32px 4px var(--accent-glow), 0 0 0 200vmax var(--scrim)",
          }}
        />
      ) : (
        <div aria-hidden="true" className="fade fixed inset-0 bg-[var(--scrim)] backdrop-blur-[3px]" />
      )}
      <div className={cx(!anchored && "fixed inset-0 flex items-center justify-center p-4")}>
        <div
          ref={card}
          key={index}
          role="dialog"
          aria-modal="true"
          aria-labelledby="tour-title"
          aria-describedby="tour-body"
          onKeyDown={trapFocus}
          className={cx("overlay fade rounded-3xl", anchored ? "fixed p-5" : "relative p-7")}
          style={cardStyle}
        >
          {welcome ? (
            <div className="mb-5 flex items-center justify-between gap-3">
              <BrandMark size={44} />
              <span className="rounded-full bg-teal-soft px-3 py-1 text-[12px] font-semibold text-teal-ink">About a minute</span>
            </div>
          ) : (
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="num text-[12.5px] text-ink-3">
                  Step {index} of {STEPS.length - 1}
                </span>
                <span className="flex items-center gap-1" aria-hidden="true">
                  {STEPS.slice(1).map((s, i) => (
                    <span key={s.title} className={cx("h-1.5 rounded-full transition-all duration-300", i + 1 === index ? "w-5 bg-accent" : i + 1 < index ? "w-1.5 bg-teal" : "w-1.5 bg-surface-3")} />
                  ))}
                </span>
              </div>
              <button type="button" className="btn btn-ghost icon-btn -mr-2 h-8 w-8 text-ink-3" onClick={onClose} aria-label="Close the tour" title="Close the tour">
                <X size={15} aria-hidden="true" />
              </button>
            </div>
          )}
          <h2 id="tour-title" className={cx("font-semibold text-ink", welcome ? "text-[24px] leading-tight tracking-[-0.01em]" : "text-[16.5px] leading-snug")}>
            {step.title}
          </h2>
          <p id="tour-body" className={cx("mt-2 leading-relaxed text-ink-2", welcome ? "text-[14.5px]" : "text-[13.5px]")}>
            {step.body}
          </p>
          <div className={cx("flex items-center justify-between gap-2", welcome ? "mt-7" : "mt-5")}>
            {last ? (
              <span />
            ) : (
              <button type="button" className="btn btn-ghost -ml-2 h-9 px-3 text-ink-3" onClick={onClose}>
                Skip tour
              </button>
            )}
            <div className="flex items-center gap-2">
              {index > 0 && (
                <button type="button" className="btn h-9 px-3.5" onClick={() => go(index - 1)}>
                  <ArrowLeft size={14} aria-hidden="true" /> Back
                </button>
              )}
              <button ref={primary} type="button" className="btn btn-primary h-9 px-4" onClick={() => (last ? onClose() : go(index + 1))}>
                {welcome ? "Show me around" : last ? "Finish" : "Next"}
                {!last && <ArrowRight size={14} aria-hidden="true" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
