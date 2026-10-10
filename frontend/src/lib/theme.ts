import { useCallback, useEffect, useState } from "react";

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "risk-engine-theme";

export function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    return "dark";
  }
  return "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    return;
  }
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(readStoredTheme);
  useEffect(() => applyTheme(theme), [theme]);
  const toggle = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);
  return { theme, toggle };
}

export interface ChartPalette {
  ink: string;
  ink2: string;
  ink3: string;
  grid: string;
  axis: string;
  accent: string;
  low: string;
  moderate: string;
  high: string;
  critical: string;
  gain: string;
  loss: string;
  neutral: string;
  surface: string;
  accentInk: string;
  surface2: string;
}

const PALETTE_VARS: Record<keyof ChartPalette, string> = {
  ink: "--ink",
  ink2: "--ink-2",
  ink3: "--ink-3",
  grid: "--chart-grid",
  axis: "--chart-axis",
  accent: "--accent",
  low: "--risk-low",
  moderate: "--risk-moderate-mark",
  high: "--risk-high",
  critical: "--risk-critical",
  gain: "--gain",
  loss: "--loss",
  neutral: "--neutral",
  surface: "--surface-solid",
  accentInk: "--accent-ink",
  surface2: "--surface-2",
};

export function readPalette(): ChartPalette {
  const style = getComputedStyle(document.documentElement);
  const entries = Object.entries(PALETTE_VARS).map(([key, variable]) => [key, style.getPropertyValue(variable).trim() || "#888888"]);
  return Object.fromEntries(entries) as ChartPalette;
}
