<script setup lang="ts">
import { onMounted, watch } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { demoModeConfiguration, refreshDemoMode } from "./demoMode";

const route = useRoute();

async function refresh(): Promise<void> {
  try {
    await refreshDemoMode();
  } catch {
    // Individual pages surface actionable API errors; the banner fails closed.
  }
}

onMounted(() => void refresh());
watch(() => route.fullPath, () => void refresh());
</script>

<template>
  <div class="app-shell">
    <div v-if="demoModeConfiguration?.demoModeEnabled" class="demo-banner" role="status">
      Demo mode — payments are simulated
    </div>
    <header class="app-header">
      <RouterLink class="brand" to="/api/queue">BrewFlow</RouterLink>
      <nav aria-label="Primary navigation">
        <RouterLink to="/api/queue">Queue</RouterLink>
        <RouterLink to="/api/history">History</RouterLink>
        <RouterLink to="/api/pos">POS</RouterLink>
        <RouterLink to="/api/configuration">Configuration</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>
