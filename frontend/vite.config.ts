import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "^/api/queue/(state|orders|completions)$": backend,
      "^/api/history/orders$": backend,
      "^/api/queue/events$": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  test: {
    environment: "jsdom",
  },
});
