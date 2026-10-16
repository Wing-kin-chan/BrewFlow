<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";

import {
  demoModeConfiguration,
  refreshDemoMode,
  saveDemoMode,
} from "../demoMode";


const loading = ref(true);
const saving = ref(false);
const error = ref("");
const checked = computed(() => demoModeConfiguration.value?.demoModePersisted ?? false);

async function load(preserveError = false): Promise<void> {
  if (!preserveError) error.value = "";
  try {
    await refreshDemoMode();
  } catch (reason) {
    if (!preserveError) {
      error.value = reason instanceof Error ? reason.message : "Unable to load configuration";
    }
  } finally {
    loading.value = false;
  }
}

async function changeMode(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const enabled = input.checked;
  saving.value = true;
  error.value = "";
  try {
    await saveDemoMode(enabled);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to update demo mode";
    await load(true);
    await nextTick();
    input.checked = checked.value;
  } finally {
    saving.value = false;
  }
}

onMounted(() => void load());
</script>

<template>
  <main class="page configuration-page">
    <section class="page-heading">
      <div><p class="eyebrow">Local settings</p><h1>Configuration</h1></div>
    </section>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section class="configuration-card">
      <h2>Payments</h2>
      <label class="toggle-row">
        <span><strong>Demo mode</strong><small>Simulate payment while preserving the POS and barista workflow.</small></span>
        <input
          type="checkbox"
          :checked="checked"
          :disabled="loading || saving || (!demoModeConfiguration?.demoModeAvailable && !checked)"
          @change="changeMode"
        />
      </label>
      <p v-if="!loading && !demoModeConfiguration?.demoModeAvailable" class="configuration-warning" role="status">
        Demo mode is unavailable unless the server starts with BREWFLOW_ALLOW_DEMO_MODE=true.
      </p>
      <p v-if="demoModeConfiguration?.demoModePersisted && !demoModeConfiguration.demoModeEnabled" class="configuration-warning" role="status">
        The saved demo setting is blocked by the server safety gate.
      </p>
    </section>
  </main>
</template>
