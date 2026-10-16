import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import PosPage from "../src/pages/PosPage.vue";
import ReceiptPage from "../src/pages/ReceiptPage.vue";
import type { PosOrderInput } from "../src/api/types";

const { toDataURL } = vi.hoisted(() => ({
  toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,qr"),
}));
vi.mock("qrcode", () => ({ default: { toDataURL } }));

const catalog = {
  currency: "gbp",
  group: "Drinks",
  items: [
    { id: "latte", name: "Latte", priceMinor: 340, milkVolume: 2, shots: 2, texture: "Wet" },
    { id: "espresso", name: "Espresso", priceMinor: 280, milkVolume: 0, shots: 2, texture: null },
  ],
  milks: ["Whole", "Semi-skimmed", "Oat", "Soy"],
  textures: ["Extra Wet", "Wet", "Dry", "Extra Dry"],
  options: ["Decaf", "Single Shot", "Extra Shot", "Extra Shot x2", "Warm", "Extra Hot"],
  milkSurchargesMinor: { "No Milk": 0, Whole: 0, "Semi-skimmed": 0, Oat: 60, Soy: 60 },
};

const checkout = {
  orderID: "00000000-0000-4000-8000-000000000001",
  status: "pending_payment",
  currency: "gbp",
  totalMinor: 800,
  items: [],
  stripeSessionID: "cs_test_1",
  checkoutURL: "https://checkout.stripe.com/test/cs_test_1",
  isDemo: false,
  demoBlocked: false,
};

beforeEach(() => {
  sessionStorage.clear();
  toDataURL.mockClear();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PosPage", () => {
  it("uses server catalog pricing, stable IDs, QR, and copy-link checkout", async () => {
    const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      if (input === "/api/pos/orders") return { ok: true, json: async () => checkout };
      if (input.startsWith("/api/pos/receipts/")) {
        return { ok: true, json: async () => ({ ...checkout, customer: "Ada", status: "pending_payment", checkoutStatus: "open", createdAt: "2026-10-09T09:00:00Z", paidAt: null, queuedAt: null }) };
      }
      throw new Error(`Unexpected request ${input} ${String(init)}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(PosPage);
    await flushPromises();

    const latte = wrapper.findAll(".menu-item").find((button) => button.text().includes("Latte"));
    await latte!.trigger("click");
    await latte!.trigger("click");
    await wrapper.findAll("select")[0].setValue("Oat");
    await wrapper.get(".basket > label input").setValue("Ada");
    expect(wrapper.text()).toContain("Quantity 2");
    expect(wrapper.text()).toContain("£8.00");

    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    const orderCall = fetchMock.mock.calls.find(([url]) => url === "/api/pos/orders");
    const submitted = JSON.parse(String((orderCall![1] as RequestInit).body));
    expect(submitted.items).toHaveLength(2);
    expect(submitted.items.every((item: Record<string, unknown>) => !("unitAmountMinor" in item))).toBe(true);
    expect(new Set(submitted.items.map((item: { identifier: string }) => item.identifier)).size).toBe(2);
    expect(toDataURL).toHaveBeenCalledWith(checkout.checkoutURL, expect.any(Object));
    expect(wrapper.get(".payment-link img").attributes("src")).toBe("data:image/png;base64,qr");
    expect(wrapper.text()).toContain("The basket is empty");
    const nextDraft = JSON.parse(sessionStorage.getItem("brewflow-pos-draft")!);
    expect(nextDraft.orderID).not.toBe(submitted.orderID);
    expect(nextDraft.lines).toEqual([]);

    const espresso = wrapper.findAll(".menu-item").find((button) => button.text().includes("Espresso"));
    await espresso!.trigger("click");
    await wrapper.get(".basket > label input").setValue("Grace");
    expect(wrapper.text()).toContain("Espresso");

    await wrapper.findAll(".payment-link button")[0].trigger("click");
    await flushPromises();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(checkout.checkoutURL);
    expect(wrapper.text()).toContain("Payment link copied");
    await wrapper.findAll(".payment-link button")[1].trigger("click");
    await flushPromises();
    const checkoutCalls = fetchMock.mock.calls.filter(([url]) => url === "/api/pos/orders");
    expect(checkoutCalls).toHaveLength(2);
    expect((checkoutCalls[1][1] as RequestInit).body).toBe((checkoutCalls[0][1] as RequestInit).body);
    wrapper.unmount();
  });

  it("retries the identical draft after a provider error", async () => {
    const submittedBodies: string[] = [];
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      if (input === "/api/pos/orders") {
        submittedBodies.push(String(init?.body));
        attempts += 1;
        if (attempts === 1) return { ok: false, status: 502, json: async () => ({}) };
        return { ok: true, json: async () => checkout };
      }
      return { ok: true, json: async () => ({ ...checkout, status: "pending_payment", checkoutStatus: "open" }) };
    }));
    const wrapper = mount(PosPage);
    await flushPromises();
    await wrapper.get(".menu-item").trigger("click");
    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Request failed (502)");
    expect(wrapper.get(".menu-item").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".basket > label input").attributes("disabled")).toBeDefined();
    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(submittedBodies).toHaveLength(2);
    expect(submittedBodies[1]).toBe(submittedBodies[0]);
    wrapper.unmount();
  });

  it("clears a submitted basket immediately without clearing the next draft when paid", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      if (input === "/api/pos/orders") return { ok: true, json: async () => checkout };
      return {
        ok: true,
        json: async () => ({
          ...checkout,
          customer: "Customer",
          status: "queued",
          checkoutStatus: "paid",
          createdAt: "2026-10-09T09:00:00Z",
          paidAt: "2026-10-09T09:01:00Z",
          queuedAt: "2026-10-09T09:01:01Z",
        }),
      };
    }));
    const wrapper = mount(PosPage);
    await flushPromises();
    await wrapper.get(".menu-item").trigger("click");
    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("The basket is empty");
    await wrapper.get(".menu-item").trigger("click");
    await new Promise((resolve) => setTimeout(resolve, 0));
    await flushPromises();
    expect(wrapper.text()).toContain("Payment received. Drinks were sent to the queue");
    expect(wrapper.text()).toContain("Quantity 1");
    expect(sessionStorage.getItem("brewflow-pos-checkout")).toBeNull();
    wrapper.unmount();
  });

  it("rekeys a stale conflicting draft before the user retries", async () => {
    const submitted: Array<{ orderID: string; items: Array<{ identifier: string }> }> = [];
    const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      if (input === "/api/pos/orders") {
        const order = JSON.parse(String(init?.body));
        submitted.push(order);
        if (submitted.length === 1) {
          return {
            ok: false,
            status: 409,
            json: async () => ({ detail: "Order identifier already has different content" }),
          };
        }
        return { ok: true, json: async () => ({ ...checkout, orderID: order.orderID }) };
      }
      return { ok: true, json: async () => ({ ...checkout, status: "pending_payment", checkoutStatus: "open" }) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(PosPage);
    await flushPromises();
    await wrapper.get(".menu-item").trigger("click");

    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("now has new identifiers");
    expect(wrapper.text()).toContain("Quantity 1");

    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(submitted).toHaveLength(2);
    expect(submitted[1].orderID).not.toBe(submitted[0].orderID);
    expect(submitted[1].items[0].identifier).not.toBe(submitted[0].items[0].identifier);
    expect(wrapper.text()).toContain("The basket is empty");
    wrapper.unmount();
  });

  it("rotates a checkout draft restored from the previous UI", async () => {
    sessionStorage.setItem(
      "brewflow-pos-draft",
      JSON.stringify({
        orderID: checkout.orderID,
        customer: "Ada",
        lines: [
          {
            identifiers: ["00000000-0000-4000-8000-000000000002"],
            catalogItemID: "latte",
            name: "Latte",
            basePriceMinor: 340,
            milkVolume: 2,
            milk: "Oat",
            texture: "Wet",
            temperature: "Normal",
            options: [],
          },
        ],
      }),
    );
    sessionStorage.setItem("brewflow-pos-checkout", JSON.stringify(checkout));
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      return {
        ok: true,
        json: async () => ({ ...checkout, status: "pending_payment", checkoutStatus: "open" }),
      };
    }));

    const wrapper = mount(PosPage);
    await flushPromises();
    expect(wrapper.text()).toContain("The basket is empty");
    const nextDraft = JSON.parse(sessionStorage.getItem("brewflow-pos-draft")!);
    expect(nextDraft.orderID).not.toBe(checkout.orderID);
    expect(JSON.parse(sessionStorage.getItem("brewflow-pos-submitted-order")!).orderID).toBe(
      checkout.orderID,
    );
    wrapper.unmount();
  });

  it("renders an inert demo QR and only submits through the demo endpoint", async () => {
    const demoCheckout = {
      ...checkout,
      isDemo: true,
      demoBlocked: false,
      stripeSessionID: null,
      checkoutURL: null,
    } as const;
    const submittedOrders: PosOrderInput[] = [];
    const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/pos/catalog") return { ok: true, json: async () => catalog };
      if (input === "/api/pos/orders") {
        const order = JSON.parse(String(init?.body)) as PosOrderInput;
        submittedOrders.push(order);
        return { ok: true, json: async () => ({ ...demoCheckout, orderID: order.orderID }) };
      }
      if (input.startsWith("/api/pos/demo-receipts/")) {
        const orderID = input.split("/").at(-1)!;
        return {
          ok: true,
          json: async () => ({
            ...demoCheckout,
            orderID,
            customer: "Ada",
            checkoutStatus: "open",
            createdAt: "2026-10-09T09:00:00Z",
            paidAt: null,
            queuedAt: null,
          }),
        };
      }
      if (input.endsWith("/demo-payment")) {
        const orderID = input.split("/").at(-2)!;
        return {
          ok: true,
          json: async () => ({
            ...demoCheckout,
            orderID,
            customer: "Ada",
            status: "queued",
            checkoutStatus: "paid",
            createdAt: "2026-10-09T09:00:00Z",
            paidAt: "2026-10-09T09:01:00Z",
            queuedAt: "2026-10-09T09:01:01Z",
          }),
        };
      }
      throw new Error(`Unexpected request ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(PosPage);
    await flushPromises();
    await wrapper.get(".menu-item").trigger("click");
    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();

    expect(toDataURL).toHaveBeenCalledWith("BREWFLOW DEMO PAYMENT", expect.any(Object));
    expect(wrapper.find(".payment-link a").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Copy payment link");
    expect(wrapper.text()).not.toContain("Waiting for verified payment");
    expect(wrapper.text()).toContain("The basket is empty");
    await wrapper.get(".menu-item").trigger("click");
    const submit = wrapper.findAll(".payment-link button").find((button) => button.text() === "Submit Payment");
    await submit!.trigger("click");
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/pos/orders/${submittedOrders[0].orderID}/demo-payment`,
      { method: "POST" },
    );
    expect(wrapper.text()).toContain("Payment received. Drinks were sent to the queue");
    expect(wrapper.text()).toContain("Quantity 1");

    await wrapper.get(".checkout-button").trigger("click");
    await flushPromises();
    expect(submittedOrders).toHaveLength(2);
    expect(submittedOrders[1].orderID).not.toBe(submittedOrders[0].orderID);
    expect(submittedOrders[1].items[0].identifier).not.toBe(submittedOrders[0].items[0].identifier);
    wrapper.unmount();
  });
});

describe("ReceiptPage", () => {
  it("loads only the sanitized receipt selected by Checkout session ID", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...checkout,
        customer: "Customer",
        status: "queued",
        checkoutStatus: "paid",
        items: [{ identifier: "drink", name: "Latte", unitAmountMinor: 400, milk: "Oat", texture: "Wet", temperature: "Normal", options: [] }],
        createdAt: "2026-10-09T09:00:00Z",
        paidAt: "2026-10-09T09:01:00Z",
          queuedAt: "2026-10-09T09:01:01Z",
          isDemo: false,
          demoBlocked: false,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/api/receipt", component: ReceiptPage }],
    });
    await router.push("/api/receipt?session_id=cs_test_1");
    await router.isReady();
    const wrapper = mount(ReceiptPage, { global: { plugins: [router] } });
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledWith("/api/pos/receipts/cs_test_1");
    expect(wrapper.text()).toContain("Paid — sent to the barista");
    expect(wrapper.text()).toContain("£4.00");
    wrapper.unmount();
  });
});
