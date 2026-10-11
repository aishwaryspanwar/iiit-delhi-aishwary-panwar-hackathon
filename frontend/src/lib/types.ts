export type EventClass =
  | "geopolitical"
  | "macroeconomic"
  | "credit_event"
  | "commodity_energy"
  | "regulatory"
  | "merger_acquisition"
  | "earnings_corporate"
  | "product_launch"
  | "other";

export type Scope = "single_name" | "sector" | "country" | "macro" | "none";
export type SentimentLabel = "neg" | "neu" | "pos";
export type EventStatus = "triggered" | "blocked" | "below";
export type AssetClass = "loan" | "bond" | "irs" | "equity" | "option";
export type Factor = "rates" | "spread" | "migration" | "equity" | "vol" | "second_order";
export type CheckName =
  | "stress_class"
  | "impact_above_threshold"
  | "confidence_ok"
  | "not_positive"
  | "direction_ok"
  | "corroborated"
  | "enough_mentions"
  | "baseline_ready"
  | "cooldown";
export type Direction = "negative" | "positive" | "neutral";

export interface Entity {
  id: string;
  name: string;
  type: "company" | "country" | "sector" | "commodity" | "central_bank" | "index";
  ticker: string | null;
  matched: string;
}

export interface BuildInfo {
  build_id: string;
  engine_version: string;
  config_hash: string;
}

export interface Signal {
  schema_version: "1.1";
  signal_id: string;
  source: string;
  source_id: string;
  url: string | null;
  outlet: string | null;
  outlets: string[];
  sources: string[];
  duplicate_count: number;
  published_at: string;
  text: string | null;
  text_hash: string;
  lang: "en";
  entities: Entity[];
  scope: Scope;
  scope_targets: string[];
  sentiment: { score: number; label: SentimentLabel; model: string };
  event: { class: EventClass; confidence: number; matched_rules: string[]; runner_up: EventClass | null; direction: Direction };
  impact: {
    score: number;
    components: { class_prior: number; sentiment_mag: number; entity_importance: number; cue_bonus: number };
    weights_version: string;
  };
  cluster_id: string | null;
  build: BuildInfo;
}

export interface WindowStats {
  n_mentions_est: number;
  n_outlets: number;
  sentiment_mean: number;
  confidence_mean: number;
  positive_share: number;
  baseline_mentions: number;
}

export interface ClusterEvent {
  schema_version: "1.1";
  cluster_id: string;
  class: EventClass;
  scope: Scope;
  scope_targets: string[];
  t_start: string;
  t_end: string;
  n_items: number;
  n_mentions: number;
  n_sources: number;
  n_outlets: number;
  sources: string[];
  sentiment_mean: number;
  confidence_mean: number;
  baseline_mentions: number;
  warmup: boolean;
  impact_components: { severity: number; breadth: number; abnormal_volume: number };
  impact: number;
  peak_at: string;
  window: WindowStats;
  detected_at: string | null;
  representative_signal_ids: string[];
}

export interface LeadSignal {
  signal_id: string;
  text: string | null;
  outlet: string | null;
  source: string;
  published_at: string;
  url: string | null;
}

export interface EventRow extends ClusterEvent {
  status: EventStatus;
  lead: LeadSignal | null;
}

export interface TriggerSettings {
  stress_classes: EventClass[];
  impact_threshold: number;
  min_confidence: number;
  max_sentiment: number;
  cooldown_hours: number;
  rearm_impact_delta: number;
  min_news_outlets: number;
  min_mentions: number;
  max_positive_share: number;
}

export interface Decision {
  cluster_id: string;
  triggered: boolean;
  checks: Partial<Record<CheckName, boolean>>;
  failed: CheckName[];
  detected_at?: string | null;
}

export interface Totals {
  value_before: number;
  value_after: number;
  pnl: number;
  pnl_pct: number;
}

export interface RunSummary {
  cluster_id: string;
  class: EventClass;
  impact: number;
  scope: Scope;
  scope_targets: string[];
  scope_label: string;
  t_start: string;
  totals: Totals;
  in_scope_positions: number;
  multiplier: number;
  lead: LeadSignal | null;
}

export interface DaySummary {
  date: string;
  signals: number;
  mentions: number;
  sentiment_sum: number;
  by_class: Partial<Record<EventClass, number>>;
  by_sentiment: Record<SentimentLabel, number>;
  by_source: Record<string, number>;
  events: number;
  above_threshold: number;
  triggered: number;
  max_event_impact: number | null;
}

export interface DatasetSummary {
  dataset: { id: string; label: string };
  live?: boolean;
  updated_at?: string | null;
  build: BuildInfo | null;
  sentiment_models: string[];
  sources: string[];
  classes: EventClass[];
  scopes: Scope[];
  totals: { signals: number; events: number; triggered: number; decisions: number };
  days: DaySummary[];
  trigger_settings: TriggerSettings;
  shocks_version: string;
  decision_failures: Partial<Record<CheckName, number>>;
  runs: RunSummary[];
}

export interface ScenarioShocks {
  source?: string;
  equity_market: number;
  sector_excess: Record<string, number>;
  rates_bp: number;
  spread_bp: { IG: number; HY: number; SAFE?: number };
  vol_pts: number;
  in_scope: { spread_bp: number; rating_notches: number; equity_excess: number };
}

export interface AppliedShocks extends ScenarioShocks {
  multiplier: number;
}

export interface Meta {
  engine_version: string;
  classes: Record<EventClass, string>;
  class_priority: EventClass[];
  rules: Record<string, { class: EventClass; weight: number; patterns: string[] }>;
  entities: Record<string, { name: string; type: string; ticker: string; sector: string; country: string }>;
  impact_weights: Record<string, number>;
  cluster_weights: Record<string, number>;
  shocks_version: string;
  trigger_settings: TriggerSettings;
  severity: { floor_multiplier: number; max_rating_notches: number };
  scenarios: Partial<Record<EventClass, ScenarioShocks>>;
  check_labels: Record<CheckName, string>;
  status_labels: Record<EventStatus, string>;
  headline: {
    max_length: number;
    examples: string[];
    outlet_range: [number, number];
    volume_options: number[];
    sentiment_model: string;
  };
}

export interface DatasetInfo {
  id: string;
  label: string;
  live?: boolean;
  updated_at?: string | null;
}

export interface SignalPage {
  total: number;
  offset: number;
  limit: number;
  items: Signal[];
}

export interface EventDetail {
  event: EventRow;
  scope_label: string;
  decision: Decision | null;
  representative_signals: Signal[];
  member_signals: Signal[];
  member_count: number;
  run: RunSummary | null;
  scenario_defined: boolean;
}

export interface SignalDetail {
  signal: Signal;
  cluster: EventDetail | null;
}

export interface FactorBreakdown extends Record<Factor, number> {
  value_before: number;
  value_after: number;
  pnl: number;
}

export interface AssetBreakdown extends FactorBreakdown {
  asset_class: AssetClass;
}

export interface PositionResult extends Record<Factor, number> {
  position_id: string;
  asset_class: AssetClass;
  name: string;
  sector: string;
  country: string;
  rating: string;
  rating_after: string;
  rating_notches: number;
  ticker: string;
  in_scope: boolean;
  contagion_weight: number;
  spread_bucket: string;
  book: "banking" | "fair_value";
  stage_before: number;
  stage_after: number;
  value_before: number;
  value_after: number;
  pnl: number;
  d_rate_bp: number;
  d_spread_bp: number;
  d_migration_spread_bp: number;
  equity_return: number;
}

export interface StressRun {
  cluster_id: string;
  class: EventClass;
  impact: number;
  scope: Scope;
  scope_targets: string[];
  t_start: string;
  shocks_applied: AppliedShocks;
  in_scope_positions: number;
  totals: Totals;
  by_asset_class: AssetBreakdown[];
  by_factor: Record<Factor, number>;
  by_book: (FactorBreakdown & { book: "banking" | "fair_value" })[];
  loan_loss_views: {
    ifrs9_provision_change: number;
    one_year_el_change: number;
    lifetime_el_change: number;
    fair_value_change: number;
    stage2_loans: number;
    stage3_loans: number;
  };
  capital: { rwa_before: number; rwa_after: number; rwa_change: number; capital_requirement_change: number; capital_ratio: number };
  severity_curve: { impact: number; multiplier: number; pnl: number }[];
  detected_at?: string;
  positions: PositionResult[];
  explanation: string;
}

export interface StressOverview {
  trigger_settings: TriggerSettings;
  shocks_version: string;
  decision_failures: Partial<Record<CheckName, number>>;
  totals: { signals: number; events: number; triggered: number; decisions: number };
  above_threshold: number;
  runs: RunSummary[];
}

export interface StressDetail {
  run: StressRun;
  summary: RunSummary;
  event: EventRow;
  decision: Decision | null;
  representative_signals: Signal[];
  base_scenario: ScenarioShocks | null;
  trigger_settings: TriggerSettings;
}

export interface PortfolioPosition {
  position_id: string;
  asset_class: AssetClass;
  name: string;
  sector: string;
  country: string;
  rating: string;
  ticker: string;
  market_value_usd: number;
  notional_usd: number | null;
}

export interface Portfolio {
  currency: string;
  total_market_value: number;
  by_asset_class: { asset_class: AssetClass; positions: number; market_value: number }[];
  positions: PortfolioPosition[];
}

export interface ScoreRequest {
  text: string;
  outlets: number;
  volume_multiple: number;
  preview: boolean;
}

export interface ScoreResult {
  signal: Signal;
  event: ClusterEvent;
  scope_label: string;
  checks: Record<Exclude<CheckName, "cooldown">, boolean>;
  triggered: boolean;
  scenario_defined: boolean;
  run: StressRun | null;
}

export interface Alert {
  schema_version: "1.0";
  alert_id: string;
  cluster_id: string;
  class: EventClass;
  scope: Scope;
  scope_targets: string[];
  scope_label: string;
  detected_at: string;
  first_headline_at: string;
  day_end_at: string;
  impact: number;
  impact_components: { severity: number; breadth: number; abnormal_volume: number };
  window: WindowStats;
  checks: Partial<Record<CheckName, boolean>>;
  representative_signal_ids: string[];
  lead: LeadSignal | null;
  pnl: number | null;
  pnl_pct: number | null;
}

export interface GeoHeadline {
  signal_id: string;
  text: string;
  outlet: string | null;
  source: string;
  published_at: string;
  impact: number;
  sentiment: number;
  sentiment_label: SentimentLabel;
  class: EventClass;
}

export interface GeoCountry {
  code: string;
  signals: number;
  mean_sentiment: number;
  max_impact: number;
  top_class: EventClass;
  by_class: Partial<Record<EventClass, number>>;
  headlines: GeoHeadline[];
}

export interface GeoSummary {
  until: string | null;
  since: string | null;
  total_signals: number;
  located_signals: number;
  countries: GeoCountry[];
}
