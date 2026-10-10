import type {
  DatasetInfo,
  DatasetSummary,
  EventDetail,
  EventRow,
  Meta,
  Portfolio,
  ScoreRequest,
  ScoreResult,
  SignalDetail,
  SignalPage,
  StressDetail,
  StressOverview,
} from "./types";

export type ApiErrorKind = "unavailable" | "invalid" | "not_found" | "bad_request" | "server";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind, message: string) {
    super(message);
    this.kind = kind;
    this.name = "ApiError";
  }
}

const UNAVAILABLE_MESSAGE =
  "Risk signal service is unavailable. Start it with `python -m src.api` from the repository root. The Streamlit reference application remains available.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return undefined;
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function request<T>(path: string, init: RequestInit | undefined, accept: (body: unknown) => boolean): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("unavailable", UNAVAILABLE_MESSAGE);
  }
  const body = await parseBody(response);
  const serverMessage = isRecord(body) && typeof body.error === "string" ? body.error : undefined;
  if (!response.ok) {
    if (response.status === 404 && serverMessage) throw new ApiError("not_found", serverMessage);
    if (response.status === 400 && serverMessage) throw new ApiError("bad_request", serverMessage);
    if (serverMessage) throw new ApiError("server", serverMessage);
    throw new ApiError("unavailable", UNAVAILABLE_MESSAGE);
  }
  if (body === undefined || !accept(body)) {
    throw new ApiError("invalid", "The risk signal service returned an unexpected response. Rebuild the processed data or restart the API.");
  }
  return body as T;
}

const hasKeys = (...keys: string[]) => (body: unknown) => isRecord(body) && keys.every((key) => key in body);
const isArray = (body: unknown) => Array.isArray(body);

const datasetPath = (dataset: string, suffix: string) => `/datasets/${encodeURIComponent(dataset)}${suffix}`;

export interface SignalQuery {
  until?: string;
  classes?: string[];
  sources?: string[];
  sentiments?: string[];
  minImpact?: number;
  q?: string;
  cluster?: string;
  sort?: "time" | "impact";
  offset?: number;
  limit?: number;
}

export function signalSearchParams(query: SignalQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.until) params.set("until", query.until);
  if (query.classes?.length) params.set("class", query.classes.join(","));
  if (query.sources?.length) params.set("source", query.sources.join(","));
  if (query.sentiments?.length) params.set("sentiment", query.sentiments.join(","));
  if (query.minImpact && query.minImpact > 1) params.set("min_impact", String(query.minImpact));
  if (query.q?.trim()) params.set("q", query.q.trim());
  if (query.cluster) params.set("cluster", query.cluster);
  if (query.sort) params.set("sort", query.sort);
  if (query.offset) params.set("offset", String(query.offset));
  if (query.limit) params.set("limit", String(query.limit));
  return params;
}

export const api = {
  meta: (signal?: AbortSignal) => request<Meta>("/meta", { signal }, hasKeys("classes", "rules", "headline")),
  datasets: (signal?: AbortSignal) => request<DatasetInfo[]>("/datasets", { signal }, isArray),
  summary: (dataset: string, signal?: AbortSignal) =>
    request<DatasetSummary>(datasetPath(dataset, "/summary"), { signal }, hasKeys("days", "totals", "runs")),
  events: (dataset: string, signal?: AbortSignal) => request<EventRow[]>(datasetPath(dataset, "/events"), { signal }, isArray),
  event: (dataset: string, clusterId: string, signal?: AbortSignal) =>
    request<EventDetail>(datasetPath(dataset, `/events/${encodeURIComponent(clusterId)}`), { signal }, hasKeys("event")),
  signals: (dataset: string, query: SignalQuery, signal?: AbortSignal) =>
    request<SignalPage>(`${datasetPath(dataset, "/signals")}?${signalSearchParams(query)}`, { signal }, hasKeys("items", "total")),
  signal: (dataset: string, signalId: string, signal?: AbortSignal) =>
    request<SignalDetail>(datasetPath(dataset, `/signals/${encodeURIComponent(signalId)}`), { signal }, hasKeys("signal")),
  stress: (dataset: string, signal?: AbortSignal) =>
    request<StressOverview>(datasetPath(dataset, "/stress"), { signal }, hasKeys("runs", "trigger_settings")),
  stressRun: (dataset: string, clusterId: string, signal?: AbortSignal) =>
    request<StressDetail>(datasetPath(dataset, `/stress/${encodeURIComponent(clusterId)}`), { signal }, hasKeys("run", "event")),
  portfolio: (signal?: AbortSignal) => request<Portfolio>("/portfolio", { signal }, hasKeys("positions")),
  score: (body: ScoreRequest, signal?: AbortSignal) =>
    request<ScoreResult>(
      "/score",
      { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" }, signal },
      hasKeys("signal", "event", "checks"),
    ),
};
