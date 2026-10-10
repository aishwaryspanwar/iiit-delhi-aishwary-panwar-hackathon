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
import alerts from "./fixtures/alerts.json";
import entities from "./fixtures/entities.json";
import entity from "./fixtures/entity.json";
import evaluation from "./fixtures/evaluation.json";

export const fixtures = { meta, datasets, summary, events, signals, signal, stress, stressRun, portfolio, alerts, entities, entity, evaluation };

const ROUTES: [RegExp, unknown][] = [
  [/\/api\/meta$/, meta],
  [/\/api\/datasets$/, datasets],
  [/\/api\/portfolio$/, portfolio],
  [/\/api\/evaluation$/, evaluation],
  [/\/api\/datasets\/[^/]+\/alerts$/, alerts],
  [/\/api\/datasets\/[^/]+\/entities$/, entities],
  [/\/api\/datasets\/[^/]+\/entities\/[^/]+$/, entity],
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
