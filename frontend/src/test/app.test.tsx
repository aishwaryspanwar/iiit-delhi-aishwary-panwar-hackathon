import { describe, expect, it } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../App";
import { THEME_STORAGE_KEY } from "../lib/theme";
import { usdMillions } from "../lib/format";
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
    const signalsCard = screen.getByText("Signals to date").closest("div")!.parentElement!;
    expect(within(signalsCard).getByText(String(fixtures.summary.totals.signals))).toBeTruthy();
    expect(screen.getByRole("group", { name: "Historical replay" })).toBeTruthy();
    expect(screen.getByText("Latest high-impact events")).toBeTruthy();
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

  it("explains the problem when the API is unavailable", async () => {
    mockApiDown();
    renderAt("#/overview");
    expect(await screen.findByText("Risk signal service unavailable")).toBeTruthy();
    expect(screen.getByText(/The Streamlit reference application remains available/)).toBeTruthy();
  });

  it("follows hash navigation between pages", async () => {
    mockApi();
    renderAt("#/overview");
    await screen.findByRole("heading", { level: 1, name: "Dashboard" });
    await act(async () => {
      window.location.hash = "#/system";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByRole("heading", { level: 1, name: "Methodology" })).toBeTruthy();
    expect(await screen.findByText("Scenario library")).toBeTruthy();
  });
});
