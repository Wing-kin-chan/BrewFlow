<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import { completeDrinks, fetchQueue } from "../api/client";
import { connectQueueEvents, type QueueEventConnection } from "../api/live";
import type { QueueSnapshot } from "../api/types";

const snapshot = ref<QueueSnapshot>({
  revision: -1,
  items: [],
  totalOrders: 0,
  totalDrinks: 0,
});
const selected = ref<string[]>([]);
const error = ref("");
const completing = ref(false);
let requestSequence = 0;
let liveConnection: QueueEventConnection | null = null;

const hasSelection = computed(() => selected.value.length > 0);

function applySnapshot(next: QueueSnapshot): void {
  if (next.revision >= snapshot.value.revision) snapshot.value = next;
  const pending = new Set(next.items.flatMap((item) => item.drinks.map((drink) => drink.identifier)));
  selected.value = selected.value.filter((identifier) => pending.has(identifier));
}

async function refresh(): Promise<void> {
  const sequence = ++requestSequence;
  try {
    const next = await fetchQueue();
    if (sequence === requestSequence) {
      applySnapshot(next);
      error.value = "";
    }
  } catch (reason) {
    if (sequence === requestSequence) {
      error.value = reason instanceof Error ? reason.message : "Unable to load the queue";
    }
  }
}

function toggleDrink(identifier: string): void {
  selected.value = selected.value.includes(identifier)
    ? selected.value.filter((value) => value !== identifier)
    : [...selected.value, identifier];
}

function toggleItem(identifiers: string[]): void {
  const allSelected = identifiers.every((identifier) => selected.value.includes(identifier));
  const next = new Set(selected.value);
  identifiers.forEach((identifier) => (allSelected ? next.delete(identifier) : next.add(identifier)));
  selected.value = [...next];
}

async function completeSelected(): Promise<void> {
  if (!hasSelection.value || completing.value) return;
  completing.value = true;
  try {
    applySnapshot(await completeDrinks(selected.value));
    selected.value = [];
    error.value = "";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to complete drinks";
  } finally {
    completing.value = false;
  }
}

onMounted(() => {
  void refresh();
  liveConnection = connectQueueEvents((event) => {
    if (event === "connected") snapshot.value.revision = -1;
    void refresh();
  });
});

onUnmounted(() => liveConnection?.close());
</script>

<template>
  <main class="page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">Live workflow</p>
        <h1>Drink queue</h1>
      </div>
      <button :disabled="!hasSelection || completing" type="button" @click="completeSelected">
        {{ completing ? "Completing…" : "Complete selected" }}
      </button>
    </section>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section class="queue" aria-label="Pending drinks" aria-live="polite">
      <article
        v-for="(item, index) in snapshot.items"
        :key="item.kind === 'order' ? item.orderID : `${item.milk}-${item.texture}-${index}`"
        class="queue-card"
      >
        <button
          class="card-heading"
          type="button"
          @click="toggleItem(item.drinks.map((drink) => drink.identifier))"
        >
          <span>{{ item.kind === "batch" ? `${item.milk} batch` : item.customer }}</span>
          <small>{{ item.kind === "batch" ? item.texture : item.timeReceived }}</small>
        </button>
        <ul>
          <li v-for="drink in item.drinks" :key="drink.identifier">
            <button
              class="drink"
              :class="{ selected: selected.includes(drink.identifier) }"
              :aria-pressed="selected.includes(drink.identifier)"
              type="button"
              @click="toggleDrink(drink.identifier)"
            >
              <strong>{{ drink.drink }}</strong>
              <span>{{ drink.customer }}</span>
              <span>{{ drink.milk }} · {{ drink.texture ?? "No texture" }}</span>
              <span>{{ drink.temperature }}</span>
              <span v-for="option in drink.options" :key="option">{{ option }}</span>
            </button>
          </li>
        </ul>
      </article>
      <p v-if="snapshot.items.length === 0" class="empty">No drinks are waiting.</p>
    </section>

    <footer class="totals">
      <span>Orders: {{ snapshot.totalOrders }}</span>
      <span>Drinks: {{ snapshot.totalDrinks }}</span>
    </footer>
  </main>
</template>
