import { describe, expect, it } from "vitest";
import { percent, safeHttpUrl, signed, usdMillions } from "../lib/format";
import { impactBand } from "../lib/risk";
import { parseHash } from "../lib/router";

describe("formatting", () => {
  it("formats money, percentages and signs with a true minus", () => {
    expect(usdMillions(-107393013.97)).toBe("−$107.4m");
    expect(usdMillions(3856101021.16)).toBe("$3,856.1m");
    expect(usdMillions(5_100_000, 1, true)).toBe("+$5.1m");
    expect(percent(-0.02785)).toBe("−2.79%");
    expect(signed(0.0001)).toBe("0.00");
  });

  it("only allows http(s) links from data", () => {
    expect(safeHttpUrl("https://www.reuters.com/a")).toBe("https://www.reuters.com/a");
    expect(safeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(safeHttpUrl(null)).toBeNull();
  });

  it("bands impact relative to the trigger threshold", () => {
    expect(impactBand(2, 7)).toBe("low");
    expect(impactBand(6.3, 7)).toBe("moderate");
    expect(impactBand(7, 7)).toBe("moderate");
    expect(impactBand(7.2, 7)).toBe("high");
    expect(impactBand(8.6, 7)).toBe("critical");
  });

  it("parses hash routes with encoded cluster ids", () => {
    expect(parseHash("#/stress/2022-02-24%7Cgeopolitical%7Ccountry%7Ccountry%3ARU")).toEqual({
      page: "stress",
      param: "2022-02-24|geopolitical|country|country:RU",
    });
    expect(parseHash("#/nowhere")).toEqual({ page: "overview", param: null });
  });
});
