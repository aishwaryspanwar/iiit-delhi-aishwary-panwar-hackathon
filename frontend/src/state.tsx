import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "./lib/api";
import { readPalette, useTheme, type ChartPalette, type Theme } from "./lib/theme";
import type { DatasetInfo, DatasetSummary, EventRow, Meta } from "./lib/types";
import { useAsync } from "./lib/useAsync";

const DATASET_STORAGE_KEY = "risk-engine-dataset";
const PLAY_INTERVAL_MS = 900;

export type DetailTarget = { kind: "signal"; id: string } | { kind: "event"; id: string };

interface Replay {
  index: number;
  last: number;
  day: string;
  playing: boolean;
  setIndex: (index: number) => void;
  step: (delta: number) => void;
  togglePlay: () => void;
}

interface AppState {
  meta: Meta;
  datasets: DatasetInfo[];
  dataset: string;
  setDataset: (id: string) => void;
  summary: DatasetSummary;
  events: EventRow[];
  replay: Replay;
  theme: Theme;
  toggleTheme: () => void;
  palette: ChartPalette;
  detail: DetailTarget | null;
  openDetail: (target: DetailTarget) => void;
  closeDetail: () => void;
  className: (value: string) => string;
  entityName: (id: string) => string;
}

const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside AppProvider");
  return value;
}

function storedDataset(): string | null {
  try {
    return window.localStorage.getItem(DATASET_STORAGE_KEY);
  } catch {
    return null;
  }
}

function rememberDataset(id: string): void {
  try {
    window.localStorage.setItem(DATASET_STORAGE_KEY, id);
  } catch {
    return;
  }
}

export interface BootState {
  phase: "loading" | "error" | "ready";
  error?: ApiError;
  retry: () => void;
}

export function AppProvider({ children, fallback }: { children: ReactNode; fallback: (state: BootState) => ReactNode }) {
  const { theme, toggle: toggleTheme } = useTheme();
  const [palette, setPalette] = useState<ChartPalette>(() => readPalette());
  useEffect(() => setPalette(readPalette()), [theme]);

  const boot = useAsync((signal) => Promise.all([api.meta(signal), api.datasets(signal)]), []);
  const [dataset, setDatasetState] = useState<string | null>(null);

  useEffect(() => {
    if (!boot.data || dataset) return;
    const [, available] = boot.data;
    const remembered = storedDataset();
    const choice = available.find((d) => d.id === remembered)?.id ?? available[0]?.id ?? null;
    setDatasetState(choice);
  }, [boot.data, dataset]);

  const data = useAsync(
    dataset ? (signal) => Promise.all([api.summary(dataset, signal), api.events(dataset, signal)]) : null,
    [dataset],
  );

  const days = data.data?.[0].days ?? [];
  const last = Math.max(days.length - 1, 0);
  const [rawIndex, setIndexState] = useState<number | null>(null);
  const index = rawIndex ?? last;
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setIndexState(null);
    setPlaying(false);
  }, [data.data]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setIndexState((stored) => {
        const current = stored ?? last;
        if (current >= last) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, PLAY_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [playing, last]);

  const setIndex = useCallback((value: number) => setIndexState(Math.min(Math.max(value, 0), last)), [last]);
  const step = useCallback((delta: number) => {
    setPlaying(false);
    setIndexState((stored) => Math.min(Math.max((stored ?? last) + delta, 0), last));
  }, [last]);
  const togglePlay = useCallback(() => {
    setPlaying((current) => {
      if (!current && index >= last) setIndexState(0);
      return !current;
    });
  }, [index, last]);

  const [detail, setDetail] = useState<DetailTarget | null>(null);
  const closeDetail = useCallback(() => setDetail(null), []);
  const setDataset = useCallback((id: string) => {
    rememberDataset(id);
    setDetail(null);
    setDatasetState(id);
  }, []);

  const value = useMemo<AppState | null>(() => {
    if (!boot.data || !data.data || !dataset || data.data[0].dataset.id !== dataset) return null;
    const [meta, datasets] = boot.data;
    const [summary, events] = data.data;
    const clampedIndex = Math.min(index, Math.max(summary.days.length - 1, 0));
    return {
      meta,
      datasets,
      dataset,
      setDataset,
      summary,
      events,
      replay: {
        index: clampedIndex,
        last: Math.max(summary.days.length - 1, 0),
        day: summary.days[clampedIndex]?.date ?? "",
        playing,
        setIndex,
        step,
        togglePlay,
      },
      theme,
      toggleTheme,
      palette,
      detail,
      openDetail: setDetail,
      closeDetail,
      className: (cls: string) => meta.classes[cls as keyof Meta["classes"]] ?? cls,
      entityName: (id: string) => meta.entities[id]?.name ?? id.split(":").pop() ?? id,
    };
  }, [boot.data, data.data, dataset, index, playing, setIndex, step, togglePlay, theme, toggleTheme, palette, detail, setDataset, closeDetail]);

  if (boot.error) return <>{fallback({ phase: "error", error: boot.error, retry: boot.reload })}</>;
  if (data.error) return <>{fallback({ phase: "error", error: data.error, retry: data.reload })}</>;
  if (boot.data && boot.data[1].length === 0) {
    return <>{fallback({ phase: "error", error: new ApiError("invalid", "No processed datasets were found. Run python -m src.pipeline --dataset stub, then restart the API."), retry: boot.reload })}</>;
  }
  if (!value) return <>{fallback({ phase: "loading", retry: boot.reload })}</>;
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
