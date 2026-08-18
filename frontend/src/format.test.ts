import { describe, expect, it } from "vitest";

import { formatPathCount } from "./format";

describe("formatPathCount", () => {
  it("formats Monte Carlo path counts for the Japanese dashboard", () => {
    expect(formatPathCount(5_000_000)).toBe("5,000,000");
    expect(formatPathCount(0)).toBe("0");
  });
});

