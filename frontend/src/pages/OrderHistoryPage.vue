<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { fetchHistory } from "../api/client";
import { connectQueueEvents, type QueueEventConnection } from "../api/live";
import type { HistorySnapshot } from "../api/types";

const snapshot = ref<HistorySnapshot>({ revision: -1, orders: [], totalOrders: 0, totalDrinks: 0 });
const error = ref("");
let requestSequence = 0;
let liveConnection: QueueEventConnection | null = null;

async function refresh(): Promise<void> {
  const sequence = ++requestSequence;
  try {
    const next = await fetchHistory();
    if (sequence === requestSequence && next.revision >= snapshot.value.revision) {
      snapshot.value = next;
      error.value = "";
    }
  } catch (reason) {
    if (sequence === requestSequence) {
      error.value = reason instanceof Error ? reason.message : "Unable to load history";
    }
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
        <p class="eyebrow">Current service day</p>
        <h1>Order history</h1>
      </div>
    </section>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section class="queue history" aria-label="Completed orders" aria-live="polite">
      <article v-for="order in snapshot.orders" :key="order.orderID" class="queue-card">
        <div class="card-heading static-heading">
          <span>{{ order.customer }}</span>
          <small>{{ order.timeComplete }}</small>
        </div>
        <ul>
          <li v-for="drink in order.drinks" :key="drink.identifier" class="completed-drink">
            <strong>{{ drink.drink }}</strong>
            <span>{{ drink.milk }}</span>
            <span>{{ drink.temperature }}</span>
          </li>
        </ul>
      </article>
      <p v-if="snapshot.orders.length === 0" class="empty">No drinks have been completed.</p>
    </section>
    <footer class="totals">
      <span>Orders: {{ snapshot.totalOrders }}</span>
      <span>Drinks: {{ snapshot.totalDrinks }}</span>
    </footer>
  </main>
</template>
