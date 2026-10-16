import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import App from "../src/App.vue";
import {
  demoModeConfiguration,
  refreshDemoMode,
  saveDemoMode,
} from "../src/demoMode";
import ConfigurationPage from "../src/pages/ConfigurationPage.vue";


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("demo mode configuration", () => {
  it("does not let a refresh started before a successful mutation overwrite it", async () => {
    let resolveStale!: (response: { ok: boolean; json: () => Promise<unknown> }) => void;
    const staleResponse = new Promise<{ ok: boolean; json: () => Promise<unknown> }>(
      (resolve) => { resolveStale = resolve; },
    );
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            demoModeEnabled: true,
            demoModePersisted: true,
            demoModeAvailable: true,
          }),
        });
      }
      if (input === "/api/configuration/demo-mode") return staleResponse;
      throw new Error(`Unexpected request ${input}`);
    }));

    const staleRefresh = refreshDemoMode();
    await saveDemoMode(true);
    resolveStale({
      ok: true,
      json: async () => ({
        demoModeEnabled: false,
        demoModePersisted: false,
        demoModeAvailable: true,
      }),
    });
    await staleRefresh;

    expect(demoModeConfiguration.value?.demoModeEnabled).toBe(true);
  });

  it("does not let a pre-mutation refresh overwrite a failed mutation refetch", async () => {
    let resolveStale!: (response: { ok: boolean; json: () => Promise<unknown> }) => void;
    let getCalls = 0;
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: async () => ({ detail: "Disable failed" }),
        });
      }
      if (input === "/api/configuration/demo-mode" && getCalls++ === 0) {
        return new Promise<{ ok: boolean; json: () => Promise<unknown> }>(
          (resolve) => { resolveStale = resolve; },
        );
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({
          demoModeEnabled: true,
          demoModePersisted: true,
          demoModeAvailable: true,
        }),
      });
    }));

    const staleRefresh = refreshDemoMode();
    await expect(saveDemoMode(false)).rejects.toThrow("Disable failed");
    await refreshDemoMode();
    resolveStale({
      ok: true,
      json: async () => ({
        demoModeEnabled: false,
        demoModePersisted: false,
        demoModeAvailable: true,
      }),
    });
    await staleRefresh;

    expect(demoModeConfiguration.value?.demoModeEnabled).toBe(true);
  });

  it("uses the authoritative API for the toggle", async () => {
    let enabled = false;
    const fetchMock = vi.fn(async (_input: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        enabled = JSON.parse(String(init.body)).demoModeEnabled;
      }
      return {
        ok: true,
        json: async () => ({
          demoModeEnabled: enabled,
          demoModePersisted: enabled,
          demoModeAvailable: true,
        }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(ConfigurationPage);
    await flushPromises();
    await wrapper.get('input[type="checkbox"]').setValue(true);
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/configuration/demo-mode",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ demoModeEnabled: true }),
      }),
    );
    expect(wrapper.get('input[type="checkbox"]').element).toHaveProperty("checked", true);
  });

  it("keeps a failed disable visible while restoring authoritative state", async () => {
    let getCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (_input: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: "Unable to finish paid demo orders" }),
        };
      }
      getCalls += 1;
      return {
        ok: true,
        json: async () => ({
          demoModeEnabled: true,
          demoModePersisted: true,
          demoModeAvailable: true,
        }),
      };
    }));
    const wrapper = mount(ConfigurationPage);
    await flushPromises();
    await wrapper.get('input[type="checkbox"]').setValue(false);
    await flushPromises();

    expect(getCalls).toBe(2);
    expect(wrapper.get('[role="alert"]').text()).toContain(
      "Unable to finish paid demo orders",
    );
    expect(wrapper.get('input[type="checkbox"]').element).toHaveProperty("checked", true);
  });

  it("shows the shared banner above every routed page after authoritative refresh", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        demoModeEnabled: true,
        demoModePersisted: true,
        demoModeAvailable: true,
      }),
    }));
    const Page = { template: '<main><section class="page-heading"><h1>Page</h1></section></main>' };
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/api/queue", component: Page },
        { path: "/api/receipt", component: Page },
      ],
    });
    await router.push("/api/queue");
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [router] } });
    await flushPromises();
    expect(wrapper.find(".demo-banner").text()).toContain("Demo mode");
    expect(wrapper.find(".demo-banner").element.compareDocumentPosition(
      wrapper.find(".app-header").element,
    ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await router.push("/api/receipt?session_id=cs_test_1");
    await flushPromises();
    expect(wrapper.find(".demo-banner").exists()).toBe(true);
    wrapper.unmount();
  });
});
