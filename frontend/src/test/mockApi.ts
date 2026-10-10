import { vi } from "vitest";
import meta from "./fixtures/meta.json";
import datasets from "./fixtures/datasets.json";
import summary from "./fixtures/summary.json";
import events from "./fixtures/events.json";
import signals from "./fixtures/signals.json";
import signal from "./fixtures/signal.json";
import stress from "./fixtures/stress.json";
import stressRun from "./fixtures/stressRun.json";
import portfolio from "./fixtures/portfolio.json";

export const fixtures = { meta, datasets, summary, events, signals, signal, stress, stressRun, portfolio };

const ROUTES: [RegExp, unknown][] = [
  [/\/api\/meta$/, meta],
  [/\/api\/datasets$/, datasets],
  [/\/api\/portfolio$/, portfolio],
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

export function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const match = ROUTES.find(([pattern]) => pattern.test(url));
    return match ? json(match[1]) : json({ error: "Unknown endpoint" }, 404);
  });
}

export function mockApiDown() {
  return vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
}
