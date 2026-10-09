import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import OrderHistoryPage from "../src/pages/OrderHistoryPage.vue";
import QueuePage from "../src/pages/QueuePage.vue";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  listeners = new Map<string, Array<(event: { data?: string }) => void>>();

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  addEventListener(name: string, listener: (event: { data?: string }) => void) {
    this.listeners.set(name, [...(this.listeners.get(name) ?? []), listener]);
  }

  emit(name: string, event: { data?: string } = {}) {
    this.listeners.get(name)?.forEach((listener) => listener(event));
  }

  close() {}
}

const drink = {
  orderID: "order-1",
  drink: "Latte",
  milk: "Whole",
  milk_volume: 2,
  shots: 2,
  temperature: "Normal",
  texture: "Wet",
  options: [],
  customer: "Ada",
  identifier: "drink-1",
  timeReceived: "09:00:00",
  timeComplete: null,
};

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("QueuePage", () => {
  it("renders a snapshot and completes selected drinks by identifier", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revision: 1, items: [{ kind: "order", orderID: "order-1", customer: "Ada", timeReceived: "09:00:00", drinks: [drink] }], totalOrders: 1, totalDrinks: 1 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revision: 2, items: [], totalOrders: 0, totalDrinks: 0 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(QueuePage);
    await flushPromises();
    expect(wrapper.text()).toContain("Latte");

    await wrapper.get(".drink").trigger("click");
    await wrapper.get(".page-heading button").trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/queue/completions",
      expect.objectContaining({ body: JSON.stringify({ drinkIDs: ["drink-1"] }) }),
    );
    expect(wrapper.text()).toContain("No drinks are waiting");
    wrapper.unmount();
  });

  it("does not replace a newer snapshot with a stale response", async () => {
    type MockResponse = { ok: boolean; json: () => Promise<unknown> };
    let resolveFirst!: (response: MockResponse) => void;
    let resolveSecond!: (response: MockResponse) => void;
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => new Promise<MockResponse>((resolve) => (resolveFirst = resolve)))
      .mockImplementationOnce(() => new Promise<MockResponse>((resolve) => (resolveSecond = resolve)));
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(QueuePage);
    await Promise.resolve();
    FakeWebSocket.instances[0].emit("open");
    resolveSecond({
      ok: true,
      json: async () => ({
        revision: 2,
        items: [{ kind: "order", orderID: "order-2", customer: "Grace", timeReceived: "09:01:00", drinks: [{ ...drink, orderID: "order-2", identifier: "drink-2", drink: "Cappuccino", customer: "Grace" }] }],
        totalOrders: 1,
        totalDrinks: 1,
      }),
    });
    await flushPromises();
    resolveFirst({
      ok: true,
      json: async () => ({ revision: 1, items: [{ kind: "order", orderID: "order-1", customer: "Ada", timeReceived: "09:00:00", drinks: [drink] }], totalOrders: 1, totalDrinks: 1 }),
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Cappuccino");
    expect(wrapper.text()).not.toContain("Latte");
    wrapper.unmount();
  });

  it("accepts an authoritative lower revision after reconnect", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revision: 40, items: [{ kind: "order", orderID: "old", customer: "Ada", timeReceived: "09:00:00", drinks: [drink] }], totalOrders: 1, totalDrinks: 1 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revision: 0, items: [], totalOrders: 0, totalDrinks: 0 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(QueuePage);
    await flushPromises();
    expect(wrapper.text()).toContain("Latte");

    FakeWebSocket.instances[0].emit("close");
    await vi.advanceTimersByTimeAsync(500);
    FakeWebSocket.instances[1].emit("open");
    await flushPromises();

    expect(wrapper.text()).toContain("No drinks are waiting");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
});

describe("OrderHistoryPage", () => {
  it("groups completed drinks beneath their original order", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          revision: 2,
          orders: [{ orderID: "order-1", customer: "Ada", dateReceived: "2026-01-01", timeReceived: "09:00:00", timeComplete: "09:05:00", drinks: [{ ...drink, timeComplete: "09:05:00" }] }],
          totalOrders: 1,
          totalDrinks: 1,
        }),
      }),
    );

    const wrapper = mount(OrderHistoryPage);
    await flushPromises();
    expect(wrapper.text()).toContain("Ada");
    expect(wrapper.text()).toContain("Latte");
    wrapper.unmount();
  });

  it("accepts an authoritative lower revision after reconnect", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          revision: 50,
          orders: [{ orderID: "old", customer: "Ada", dateReceived: "2026-01-01", timeReceived: "09:00:00", timeComplete: "09:05:00", drinks: [{ ...drink, timeComplete: "09:05:00" }] }],
          totalOrders: 1,
          totalDrinks: 1,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revision: 0, orders: [], totalOrders: 0, totalDrinks: 0 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(OrderHistoryPage);
    await flushPromises();
    expect(wrapper.text()).toContain("Latte");

    FakeWebSocket.instances[0].emit("close");
    await vi.advanceTimersByTimeAsync(500);
    FakeWebSocket.instances[1].emit("open");
    await flushPromises();

    expect(wrapper.text()).toContain("No drinks have been completed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
});
