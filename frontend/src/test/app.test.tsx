import { describe, expect, it } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../App";
import { THEME_STORAGE_KEY } from "../lib/theme";
import { TOUR_STORAGE_KEY } from "../components/Tour";
import { usdMillions } from "../lib/format";
import { GEO_PLACES } from "../lib/geo";
import { fixtures, mockApi, mockApiDown } from "./mockApi";

function renderAt(hash: string) {
  window.location.hash = hash;
  return render(<App />);
}

describe("React frontend", () => {
  it("renders the overview from the API with real totals", async () => {
    mockApi();
    renderAt("#/overview");
    expect(await screen.findByRole("heading", { level: 1, name: "Dashboard" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Stats" }));
    const signalsCard = screen.getByText("Signals to date").closest("div")!.parentElement!;
    expect(within(signalsCard).getByText(String(fixtures.summary.totals.signals))).toBeTruthy();
    expect(screen.getByRole("group", { name: "Historical replay" })).toBeTruthy();
    expect(screen.getByText("Latest high-impact events")).toBeTruthy();
  });

  it("shows headlines on the world map and lists a selected country's headlines", async () => {
    mockApi();
    renderAt("#/overview");
    const map = await screen.findByRole("region", { name: "Where the news is" });
    const top = fixtures.geo.countries[0];
    const bubble = await within(map).findByRole("button", { name: new RegExp(`^${GEO_PLACES[top.code].name}: ${top.signals} headlines`) });
    fireEvent.click(bubble);
    const aside = within(map).getByText("Selected country").closest("aside")!;
    expect(within(aside).getByRole("heading", { name: GEO_PLACES[top.code].name })).toBeTruthy();
    expect(within(aside).getByText(top.headlines[0].text)).toBeTruthy();
    expect(within(map).getByRole("tab", { name: "Most covered" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.click(within(aside).getByRole("button", { name: "Clear selection" }));
    expect(within(map).getByRole("heading", { name: "Most covered" })).toBeTruthy();
  });

  it("switches the map side panel between risk posture, coverage and figures", async () => {
    mockApi();
    renderAt("#/overview");
    const map = await screen.findByRole("region", { name: "Where the news is" });
    const tabs = within(map).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Risk posture", "Most covered", "Stats"]);
    expect(tabs[0].getAttribute("aria-selected")).toBe("true");
    expect(within(map).getByText(/risk$/)).toBeTruthy();
    expect(within(map).getByRole("img", { name: /^Risk scale/ })).toBeTruthy();
    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    expect(within(map).getByRole("tab", { name: "Most covered" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(within(map).getByRole("tab", { name: "Most covered" }), { key: "End" });
    expect(within(map).getByText("Stress tests fired")).toBeTruthy();
  });

  it("changes the map period from the dropdown", async () => {
    const spy = mockApi();
    renderAt("#/overview");
    const map = await screen.findByRole("region", { name: "Where the news is" });
    fireEvent.click(within(map).getByRole("tab", { name: "Most covered" }));
    const trigger = within(map).getByRole("button", { name: "Map period: Window to date" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(trigger);
    const list = within(map).getByRole("listbox", { name: "Map period" });
    expect(within(list).getAllByRole("option").map((o) => o.textContent)).toEqual(["Replay day", "7 days", "Window to date"]);
    expect(within(list).getByRole("option", { name: "Window to date" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.click(within(list).getByRole("option", { name: "7 days" }));
    expect(within(map).queryByRole("listbox")).toBeNull();
    expect(within(map).getByRole("button", { name: "Map period: 7 days" })).toBeTruthy();
    await act(async () => {});
    expect(spy.mock.calls.some(([input]) => String(input).includes("/geo?") && String(input).includes("days=7"))).toBe(true);
    fireEvent.click(within(map).getByRole("button", { name: "Map period: 7 days" }));
    fireEvent.keyDown(within(map).getByRole("listbox"), { key: "Escape" });
    expect(within(map).queryByRole("listbox")).toBeNull();
  });

  it("has map coordinates for every country the engine can tag", () => {
    const codes = Object.values(fixtures.meta.entities)
      .filter((entity) => ["country", "central_bank", "index"].includes(entity.type) && entity.country)
      .map((entity) => entity.country as string);
    expect(codes.filter((code) => !GEO_PLACES[code])).toEqual([]);
  });

  it("switches between offline datasets and the live feed in the header", async () => {
    mockApi();
    const view = renderAt("#/overview");
    await screen.findByRole("heading", { level: 1, name: "Dashboard" });
    const source = screen.getByRole("radiogroup", { name: "Data source" });
    expect(within(source).getByRole("radio", { name: "Offline" }).getAttribute("aria-checked")).toBe("true");
    expect(within(source).getByRole("radio", { name: "Live" }).getAttribute("aria-disabled")).toBe("true");
    const picker = screen.getByRole("button", { name: `Dataset: ${fixtures.datasets[0].label}` });
    fireEvent.click(picker);
    expect(within(screen.getByRole("listbox", { name: "Dataset" })).getAllByRole("option").map((o) => o.textContent)).toEqual(fixtures.datasets.map((d) => d.label));
    view.unmount();
    mockApi({ live: true, updated_at: "2026-10-10T22:45:00Z" });
    renderAt("#/overview");
    await screen.findByRole("heading", { level: 1, name: "Dashboard" });
    expect(screen.getByRole("radio", { name: "Live" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByText("Updated 04:15 IST")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^Dataset:/ })).toBeNull();
  });

  it("walks a first-time visitor through the tour and can be skipped at every step", async () => {
    window.localStorage.removeItem(TOUR_STORAGE_KEY);
    mockApi();
    renderAt("#/stress");
    const welcome = await screen.findByRole("dialog", { name: "Welcome to Ripple" });
    fireEvent.click(within(welcome).getByRole("button", { name: "Show me around" }));
    const step = await screen.findByRole("dialog", { name: "Four pages" });
    expect(window.location.hash).toBe("#/overview");
    expect(within(step).getByText("Step 1 of 6")).toBeTruthy();
    expect(within(step).getByRole("button", { name: "Skip tour" })).toBeTruthy();
    fireEvent.click(within(step).getByRole("button", { name: /Next/ }));
    expect(await screen.findByRole("dialog", { name: "Choose your data" })).toBeTruthy();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Choose your data" })).toBeNull();
    expect(window.localStorage.getItem(TOUR_STORAGE_KEY)).toBe("done");
    fireEvent.click(screen.getByRole("button", { name: "Take the tour" }));
    const again = await screen.findByRole("dialog", { name: "Welcome to Ripple" });
    fireEvent.click(within(again).getByRole("button", { name: "Skip tour" }));
    expect(screen.queryByRole("dialog", { name: "Welcome to Ripple" })).toBeNull();
  });

  it("toggles and persists the theme", async () => {
    mockApi();
    renderAt("#/overview");
    await screen.findByRole("heading", { level: 1, name: "Dashboard" });
    expect(document.documentElement.dataset.theme).toBe("dark");
    fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("renders the signal feed and opens the explainability drawer", async () => {
    mockApi();
    renderAt("#/signals");
    const first = fixtures.signals.items[0];
    const cell = await screen.findByRole("button", { name: first.text ?? "" });
    expect(screen.getByText(`Showing 1–${fixtures.signals.items.length} of ${fixtures.signals.total} signals`)).toBeTruthy();
    fireEvent.click(cell);
    const dialog = await screen.findByRole("dialog", { name: "Signal detail" });
    expect(await within(dialog).findByText("Why this impact score")).toBeTruthy();
    expect(within(dialog).getByText(first.signal_id)).toBeTruthy();
  });

  it("shows the stress test before and after values from the engine", async () => {
    mockApi();
    renderAt("#/stress");
    const totals = fixtures.stressRun.run.totals;
    expect(await screen.findByText("Causal chain")).toBeTruthy();
    expect(screen.getAllByText(usdMillions(totals.value_before)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(usdMillions(totals.value_after)).length).toBeGreaterThan(0);
    expect(screen.getByText("Position-level results")).toBeTruthy();
    expect(screen.getByText(fixtures.stressRun.run.explanation)).toBeTruthy();
  });

  it("shows real-time alerts with detection times on the overview", async () => {
    mockApi();
    renderAt("#/overview");
    expect(await screen.findByText("Real-time alerts")).toBeTruthy();
    expect(await screen.findAllByText(/h early/)).toBeTruthy();
  });

  it("shows credit losses, capital and the severity curve for a stress run", async () => {
    mockApi();
    renderAt("#/stress");
    expect(await screen.findByText("Credit losses and capital")).toBeTruthy();
    expect(screen.getByText("Severity curve")).toBeTruthy();
    expect(screen.getByText("IFRS 9 provisions (headline)")).toBeTruthy();
  });

  it("explains the problem when the API is unavailable", async () => {
    mockApiDown();
    renderAt("#/overview");
    expect(await screen.findByText("Risk signal service unavailable")).toBeTruthy();
    expect(screen.getByText(/Start it with `python -m src.api`/)).toBeTruthy();
  });

  it("follows hash navigation between pages", async () => {
    mockApi();
    renderAt("#/overview");
    await screen.findByRole("heading", { level: 1, name: "Dashboard" });
    await act(async () => {
      window.location.hash = "#/stress";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByRole("heading", { level: 1, name: "Portfolio stress test" })).toBeTruthy();
  });

  it("offers only the four product pages and falls back to the overview", async () => {
    mockApi();
    renderAt("#/evaluation");
    expect(await screen.findByRole("heading", { level: 1, name: "Dashboard" })).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Overview", "Signal feed", "Stress test", "Try a headline"]);
  });
});
