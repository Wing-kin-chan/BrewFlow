import { readonly, ref } from "vue";

import { fetchDemoMode, updateDemoMode } from "./api/client";
import type { DemoModeConfiguration } from "./api/types";


const configuration = ref<DemoModeConfiguration | null>(null);
let refreshSequence = 0;
let mutationEpoch = 0;
let activeMutations = 0;

export const demoModeConfiguration = readonly(configuration);

export async function refreshDemoMode(): Promise<DemoModeConfiguration> {
  const sequence = ++refreshSequence;
  const epoch = mutationEpoch;
  const startedDuringMutation = activeMutations > 0;
  try {
    const authoritative = await fetchDemoMode();
    if (
      sequence === refreshSequence &&
      epoch === mutationEpoch &&
      !startedDuringMutation
    ) {
      configuration.value = authoritative;
    }
    return authoritative;
  } catch (error) {
    if (
      sequence === refreshSequence &&
      epoch === mutationEpoch &&
      !startedDuringMutation
    ) {
      configuration.value = null;
    }
    throw error;
  }
}

export async function saveDemoMode(enabled: boolean): Promise<DemoModeConfiguration> {
  const epoch = ++mutationEpoch;
  activeMutations += 1;
  try {
    const authoritative = await updateDemoMode(enabled);
    if (epoch === mutationEpoch) configuration.value = authoritative;
    return authoritative;
  } finally {
    activeMutations -= 1;
  }
}
