<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";

import { fetchReceipt } from "../api/client";
import type { Receipt } from "../api/types";

const route = useRoute();
const receipt = ref<Receipt | null>(null);
const error = ref("");
let timer: ReturnType<typeof setTimeout> | null = null;

function money(amount: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(amount / 100);
}

async function refresh(): Promise<void> {
  const sessionID = typeof route.query.session_id === "string" ? route.query.session_id : "";
  if (!sessionID) {
    error.value = "Receipt session is missing.";
    return;
  }
  try {
    receipt.value = await fetchReceipt(sessionID);
    error.value = "";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to load receipt";
  } finally {
    if (receipt.value?.status !== "queued" && receipt.value?.checkoutStatus !== "expired") {
      timer = setTimeout(() => void refresh(), 2000);
    }
  }
}

onMounted(() => void refresh());
onUnmounted(() => { if (timer !== null) clearTimeout(timer); });
</script>

<template>
  <main class="page receipt-page">
    <section class="page-heading"><div><p class="eyebrow">Stripe payment</p><h1>Order receipt</h1></div></section>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="receipt" class="receipt-card">
      <p class="receipt-status" role="status">{{ receipt.status === "queued" ? "Paid — sent to the barista" : receipt.checkoutStatus === "expired" ? "This payment link expired" : "Confirming payment…" }}</p>
      <h2>{{ receipt.customer }}</h2>
      <ul><li v-for="item in receipt.items" :key="item.identifier"><span><strong>{{ item.name }}</strong><small>{{ item.milk }} · {{ item.texture ?? "No texture" }} · {{ item.temperature }}<template v-if="item.options.length"> · {{ item.options.join(", ") }}</template></small></span><strong>{{ money(item.unitAmountMinor) }}</strong></li></ul>
      <p class="basket-total"><span>Total</span><strong>{{ money(receipt.totalMinor) }}</strong></p>
    </section>
  </main>
</template>
