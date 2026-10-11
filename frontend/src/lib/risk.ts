import type { AssetClass, CheckName, EventStatus, Factor, SentimentLabel } from "./types";

export type RiskBand = "low" | "moderate" | "high" | "critical";

export const MODERATE_FROM = 4;

export function criticalFrom(threshold: number): number {
  return (threshold + 10) / 2;
}

export function impactBand(impact: number, threshold: number): RiskBand {
  if (impact >= criticalFrom(threshold)) return "critical";
  if (impact > threshold) return "high";
  if (impact >= MODERATE_FROM) return "moderate";
  return "low";
}

export const BAND_LABELS: Record<RiskBand, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  critical: "Critical",
};

export const STATUS_TEXT: Record<EventStatus, string> = {
  triggered: "Stress test triggered",
  blocked: "Above threshold, blocked",
  below: "Below threshold",
};

export const SENTIMENT_TEXT: Record<SentimentLabel, string> = {
  neg: "Negative",
  neu: "Neutral",
  pos: "Positive",
};

export const SOURCE_TEXT: Record<string, string> = {
  gdelt_gkg: "GDELT news",
  gdelt_live: "GDELT live feed",
  kaggle_tweets: "Stock tweets",
  stub_news: "Stub news",
  stub_tweets: "Stub tweets",
  user_input: "Your text",
};

export function assetChange(row: { asset_class: AssetClass; value_before: number; pnl: number }): number | null {
  if (row.asset_class === "irs" || row.value_before === 0 || Math.abs(row.pnl) > Math.abs(row.value_before)) return null;
  return row.pnl / Math.abs(row.value_before);
}

export const ASSET_TEXT: Record<AssetClass, string> = {
  loan: "Loans",
  bond: "Bonds",
  irs: "Interest-rate swaps",
  equity: "Equities",
  option: "Equity options",
};

export const FACTOR_TEXT: Record<Factor, string> = {
  rates: "Rates",
  spread: "Credit spread",
  migration: "Migration and provisions",
  equity: "Equity",
  vol: "Volatility",
  second_order: "Convexity",
};

export const FACTOR_ORDER: Factor[] = ["rates", "spread", "migration", "equity", "vol", "second_order"];

export const SCOPE_TEXT: Record<string, string> = {
  single_name: "Single name",
  sector: "Sector",
  country: "Country",
  macro: "Macro",
  none: "No scope",
};

export const CHECK_ORDER: CheckName[] = [
  "stress_class",
  "impact_above_threshold",
  "confidence_ok",
  "not_positive",
  "direction_ok",
  "corroborated",
  "enough_mentions",
  "baseline_ready",
  "cooldown",
];
