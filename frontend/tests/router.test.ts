import { describe, expect, it } from "vitest";

import { routes } from "../src/router";

describe("router", () => {
  it("exposes the implemented Queue, History, POS, receipt, and Configuration pages", () => {
    expect(routes.map((route) => route.path)).toEqual([
      "/",
      "/api/queue",
      "/api/history",
      "/api/pos",
      "/api/receipt",
      "/api/configuration",
    ]);
  });
});
