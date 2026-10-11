import { vi } from "vitest";
import meta from "./fixtures/meta.json";
import datasets from "./fixtures/datasets.json";
import summary from "./fixtures/summary.json";
import events from "./fixtures/events.json";
import signals from "./fixtures/signals.json";
import signal from "./fixtures/signal.json";
import stress from "./fixtures/stress.json";
import stressRun from "./fixtures/stressRun.json";
import alerts from "./fixtures/alerts.json";
import geo from "./fixtures/geo.json";

export const fixtures = { meta, datasets, summary, events, signals, signal, stress, stressRun, alerts, geo };

const ROUTES: [RegExp, unknown][] = [
  [/\/api\/meta$/, meta],
  [/\/api\/datasets$/, datasets],
  [/\/api\/datasets\/[^/]+\/alerts$/, alerts],
  [/\/api\/datasets\/[^/]+\/geo\?/, geo],
  [/\/api\/datasets\/[^/]+\/summary$/, summary],
  [/\/api\/datasets\/[^/]+\/events$/, events],
  [/\/api\/datasets\/[^/]+\/signals\?/, signals],
  [/\/api\/datasets\/[^/]+\/signals\/[^/]+$/, signal],
  [/\/api\/datasets\/[^/]+\/stress$/, stress],
  [/\/api\/datasets\/[^/]+\/stress\/[^/]+$/, stressRun],
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function mockApi(summaryOverrides: Record<string, unknown> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const match = ROUTES.find(([pattern]) => pattern.test(url));
    if (!match) return json({ error: "Unknown endpoint" }, 404);
    return json(match[1] === summary ? { ...summary, ...summaryOverrides } : match[1]);
  });
}

export function mockApiDown() {
  return vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
}
