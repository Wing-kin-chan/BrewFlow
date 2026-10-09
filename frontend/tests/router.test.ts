import { describe, expect, it } from "vitest";

import { routes } from "../src/router";

describe("router", () => {
  it("exposes only the implemented Queue and History pages", () => {
    expect(routes.map((route) => route.path)).toEqual(["/", "/api/queue", "/api/history"]);
  });
});
