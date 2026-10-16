<script setup lang="ts">
import QRCode from "qrcode";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import {
  ApiError,
  createCheckout,
  fetchCatalog,
  fetchDemoReceipt,
  fetchReceipt,
  submitDemoPayment,
} from "../api/client";
import type {
  Catalog,
  CatalogItem,
  CheckoutResponse,
  PosOrderInput,
  Receipt,
  Temperature,
  Texture,
} from "../api/types";

interface BasketLine {
  identifiers: string[];
  catalogItemID: string;
  name: string;
  basePriceMinor: number;
  milkVolume: number;
  milk: string;
  texture: Texture | null;
  temperature: Temperature;
  options: string[];
}

interface Draft {
  orderID: string;
  customer: string;
  lines: BasketLine[];
}

const DRAFT_KEY = "brewflow-pos-draft";
const CHECKOUT_KEY = "brewflow-pos-checkout";
const SUBMITTED_ORDER_KEY = "brewflow-pos-submitted-order";
const DEMO_QR_PAYLOAD = "BREWFLOW DEMO PAYMENT";

const catalog = ref<Catalog | null>(null);
const search = ref("");
const customer = ref("");
const orderID = ref<string>(crypto.randomUUID());
const lines = ref<BasketLine[]>([]);
const checkout = ref<CheckoutResponse | null>(null);
const submittedOrder = ref<PosOrderInput | null>(null);
const qrCode = ref("");
const paymentMessage = ref("");
const error = ref("");
const loading = ref(true);
const submitting = ref(false);
const submittingPayment = ref(false);
let pollTimer: ReturnType<typeof setTimeout> | null = null;

const draftLocked = computed(
  () => submitting.value || (submittedOrder.value !== null && checkout.value === null),
);

const visibleItems = computed(() => {
  const query = search.value.trim().toLowerCase();
  return (catalog.value?.items ?? []).filter((item) => item.name.toLowerCase().includes(query));
});

const pricedTotal = computed(() =>
  lines.value.reduce(
    (total, line) => total + unitAmount(line) * line.identifiers.length,
    0,
  ),
);

const paidOptions = computed(() =>
  (catalog.value?.options ?? []).filter((option) => !["Warm", "Extra Hot"].includes(option)),
);

function money(amount: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(amount / 100);
}

function unitAmount(line: BasketLine): number {
  return line.basePriceMinor + (catalog.value?.milkSurchargesMinor[line.milk] ?? 0);
}

function defaultLine(item: CatalogItem): BasketLine {
  const hasMilk = item.milkVolume > 0;
  return {
    identifiers: [crypto.randomUUID()],
    catalogItemID: item.id,
    name: item.name,
    basePriceMinor: item.priceMinor,
    milkVolume: item.milkVolume,
    milk: hasMilk ? (catalog.value?.milks[0] ?? "Whole") : "No Milk",
    texture: hasMilk ? item.texture : null,
    temperature: "Normal",
    options: [],
  };
}

function addItem(item: CatalogItem): void {
  if (draftLocked.value) return;
  const existing = lines.value.find(
    (line) => line.catalogItemID === item.id && line.options.length === 0,
  );
  if (existing) existing.identifiers.push(crypto.randomUUID());
  else lines.value.push(defaultLine(item));
}

function increase(line: BasketLine): void {
  if (draftLocked.value) return;
  line.identifiers.push(crypto.randomUUID());
}

function decrease(line: BasketLine): void {
  if (draftLocked.value) return;
  line.identifiers.pop();
  if (line.identifiers.length === 0) {
    lines.value = lines.value.filter((candidate) => candidate !== line);
  }
}

function toggleOption(line: BasketLine, option: string): void {
  if (draftLocked.value) return;
  const shotOptions = ["Single Shot", "Extra Shot", "Extra Shot x2"];
  if (line.options.includes(option)) {
    line.options = line.options.filter((value) => value !== option);
    return;
  }
  if (shotOptions.includes(option)) {
    line.options = line.options.filter((value) => !shotOptions.includes(value));
  }
  line.options.push(option);
}

function buildOrder(): PosOrderInput {
  return {
    orderID: orderID.value,
    customer: customer.value.trim() || null,
    items: lines.value.flatMap((line) =>
      line.identifiers.map((identifier) => ({
        identifier,
        catalogItemID: line.catalogItemID,
        milk: line.milk,
        texture: line.texture,
        temperature: line.temperature,
        options: [...line.options],
      })),
    ),
  };
}

function saveDraft(): void {
  const draft: Draft = { orderID: orderID.value, customer: customer.value, lines: lines.value };
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

function setSubmittedOrder(order: PosOrderInput | null): void {
  submittedOrder.value = order;
  if (order) sessionStorage.setItem(SUBMITTED_ORDER_KEY, JSON.stringify(order));
  else sessionStorage.removeItem(SUBMITTED_ORDER_KEY);
}

function resetDraft(): void {
  orderID.value = crypto.randomUUID();
  customer.value = "";
  lines.value = [];
  saveDraft();
}

function rekeyDraft(): void {
  orderID.value = crypto.randomUUID();
  lines.value = lines.value.map((line) => ({
    ...line,
    identifiers: line.identifiers.map(() => crypto.randomUUID()),
    options: [...line.options],
  }));
  saveDraft();
}

function restoreState(): void {
  try {
    const savedDraft = JSON.parse(sessionStorage.getItem(DRAFT_KEY) ?? "null") as Draft | null;
    if (savedDraft?.orderID && Array.isArray(savedDraft.lines)) {
      orderID.value = savedDraft.orderID;
      customer.value = savedDraft.customer ?? "";
      lines.value = savedDraft.lines;
    }
    const savedCheckout = JSON.parse(
      sessionStorage.getItem(CHECKOUT_KEY) ?? "null",
    ) as CheckoutResponse | null;
    if (
      savedCheckout?.orderID &&
      (savedCheckout.isDemo === true ||
        (savedCheckout.isDemo === false &&
          Boolean(savedCheckout.checkoutURL) &&
          Boolean(savedCheckout.stripeSessionID)))
    ) {
      checkout.value = savedCheckout;
    }
    const savedSubmission = JSON.parse(
      sessionStorage.getItem(SUBMITTED_ORDER_KEY) ?? "null",
    ) as PosOrderInput | null;
    if (
      savedSubmission?.orderID &&
      Array.isArray(savedSubmission.items) &&
      (checkout.value
        ? savedSubmission.orderID === checkout.value.orderID
        : savedSubmission.orderID === orderID.value)
    ) {
      submittedOrder.value = savedSubmission;
    } else {
      sessionStorage.removeItem(SUBMITTED_ORDER_KEY);
    }
    if (checkout.value && orderID.value === checkout.value.orderID && lines.value.length) {
      // Upgrade a checkout saved by the previous UI (or finish an interrupted
      // successful submission) before this identifier can be reused.
      if (!submittedOrder.value) setSubmittedOrder(buildOrder());
      resetDraft();
    }
  } catch {
    sessionStorage.removeItem(DRAFT_KEY);
    sessionStorage.removeItem(CHECKOUT_KEY);
    sessionStorage.removeItem(SUBMITTED_ORDER_KEY);
  }
}

async function setCheckout(next: CheckoutResponse): Promise<void> {
  checkout.value = next;
  sessionStorage.setItem(CHECKOUT_KEY, JSON.stringify(next));
  const payload = next.isDemo ? DEMO_QR_PAYLOAD : next.checkoutURL;
  try {
    qrCode.value = await QRCode.toDataURL(payload, { width: 220, margin: 1 });
  } catch {
    qrCode.value = "";
    error.value = "Payment was created, but its QR code could not be displayed.";
  }
  scheduleReceiptPoll(0);
}

async function submitOrder(): Promise<void> {
  if ((!lines.value.length && !submittedOrder.value) || submitting.value || checkout.value) return;
  submitting.value = true;
  error.value = "";
  const submission = submittedOrder.value ?? buildOrder();
  if (!submittedOrder.value) setSubmittedOrder(submission);
  try {
    const nextCheckout = await createCheckout(submission);
    const checkoutSetup = setCheckout(nextCheckout);
    resetDraft();
    await checkoutSetup;
  } catch (reason) {
    if (reason instanceof ApiError && reason.status === 409) {
      setSubmittedOrder(null);
      rekeyDraft();
      error.value =
        "That order identifier was already submitted. This basket now has new identifiers; review it and create payment again.";
    } else {
      if (reason instanceof ApiError && reason.status === 422) setSubmittedOrder(null);
      error.value = reason instanceof Error ? reason.message : "Unable to start checkout";
    }
  } finally {
    submitting.value = false;
  }
}

async function refreshPaymentLink(): Promise<void> {
  const submission = submittedOrder.value;
  if (!submission || submitting.value) return;
  submitting.value = true;
  error.value = "";
  try {
    await setCheckout(await createCheckout(submission));
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to refresh payment link";
  } finally {
    submitting.value = false;
  }
}

async function copyLink(): Promise<void> {
  if (!checkout.value || checkout.value.isDemo) return;
  try {
    await navigator.clipboard.writeText(checkout.value.checkoutURL);
    paymentMessage.value = "Payment link copied.";
  } catch {
    error.value = "Unable to copy the payment link.";
  }
}

function applyReceipt(receipt: Receipt, expectedOrderID: string): boolean {
  if (checkout.value?.orderID !== expectedOrderID) return true;
  if (receipt.status === "queued") {
    paymentMessage.value = "Payment received. Drinks were sent to the queue.";
    checkout.value = null;
    qrCode.value = "";
    sessionStorage.removeItem(CHECKOUT_KEY);
    setSubmittedOrder(null);
    return true;
  }
  if (receipt.demoBlocked) {
    paymentMessage.value = "Demo payment is paused because demo mode is disabled.";
    return true;
  }
  if (receipt.checkoutStatus === "expired") {
    paymentMessage.value = "The payment link expired. Create a replacement to continue.";
    return true;
  }
  return false;
}

async function completeDemoPayment(): Promise<void> {
  const current = checkout.value;
  if (!current?.isDemo || submittingPayment.value) return;
  submittingPayment.value = true;
  error.value = "";
  try {
    applyReceipt(await submitDemoPayment(current.orderID), current.orderID);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to submit demo payment";
  } finally {
    submittingPayment.value = false;
  }
}

async function pollReceipt(): Promise<void> {
  if (!checkout.value) return;
  try {
    const current = checkout.value;
    const receipt = current.isDemo
      ? await fetchDemoReceipt(current.orderID)
      : await fetchReceipt(current.stripeSessionID);
    if (checkout.value?.orderID !== current.orderID) return;
    if (applyReceipt(receipt, current.orderID)) return;
  } catch {
    // A transient polling error must not create another checkout.
  }
  scheduleReceiptPoll(2000);
}

function scheduleReceiptPoll(delay: number): void {
  if (pollTimer !== null) clearTimeout(pollTimer);
  pollTimer = setTimeout(() => void pollReceipt(), delay);
}

watch([orderID, customer, lines], saveDraft, { deep: true });

onMounted(async () => {
  restoreState();
  try {
    catalog.value = await fetchCatalog();
    if (checkout.value) await setCheckout(checkout.value);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unable to load the menu";
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  if (pollTimer !== null) clearTimeout(pollTimer);
});
</script>

<template>
  <main class="page pos-page">
    <section class="page-heading">
      <div><p class="eyebrow">Local point of sale</p><h1>Drinks</h1></div>
      <input v-model="search" aria-label="Search menu" placeholder="Search drinks" type="search" />
    </section>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="paymentMessage" class="success" role="status">{{ paymentMessage }}</p>

    <section class="pos-layout">
      <div class="menu-panel" aria-label="Drink menu">
        <p v-if="loading">Loading menu…</p>
        <button v-for="item in visibleItems" :key="item.id" class="menu-item" :disabled="draftLocked" type="button" @click="addItem(item)">
          <strong>{{ item.name }}</strong><span>{{ money(item.priceMinor) }}</span>
        </button>
      </div>

      <aside class="basket" aria-label="Customer basket">
        <label>Customer name <input v-model="customer" :disabled="draftLocked" maxlength="100" placeholder="Optional" /></label>
        <article v-for="line in lines" :key="line.identifiers[0]" class="basket-line">
          <header><strong>{{ line.name }}</strong><span>{{ money(unitAmount(line)) }}</span></header>
          <div class="quantity">
            <button :disabled="draftLocked" aria-label="Decrease quantity" type="button" @click="decrease(line)">−</button>
            <span>Quantity {{ line.identifiers.length }}</span>
            <button :disabled="draftLocked" aria-label="Increase quantity" type="button" @click="increase(line)">+</button>
          </div>
          <template v-if="line.milkVolume > 0">
            <label>Milk <select v-model="line.milk" :disabled="draftLocked"><option v-for="milk in catalog?.milks" :key="milk">{{ milk }}</option></select></label>
            <label>Texture <select v-model="line.texture" :disabled="draftLocked"><option v-for="texture in catalog?.textures" :key="texture">{{ texture }}</option></select></label>
          </template>
          <label>Temperature <select v-model="line.temperature" :disabled="draftLocked"><option>Warm</option><option>Normal</option><option>Extra Hot</option></select></label>
          <fieldset :disabled="draftLocked"><legend>Options</legend><label v-for="option in paidOptions" :key="option"><input :checked="line.options.includes(option)" type="checkbox" @change="toggleOption(line, option)" />{{ option }}</label></fieldset>
        </article>
        <p v-if="!lines.length" class="empty">The basket is empty.</p>
        <div class="basket-total"><span>Total</span><strong>{{ money(pricedTotal) }}</strong></div>
        <button class="checkout-button" :disabled="(!lines.length && !submittedOrder) || submitting || !!checkout" type="button" @click="submitOrder()">
          {{ submitting ? "Starting checkout…" : checkout ? "Checkout in progress" : submittedOrder ? "Retry create payment" : "Create payment" }}
        </button>
        <section v-if="checkout" class="payment-link" aria-label="Customer payment">
          <h2>Customer payment</h2>
          <img v-if="qrCode" :src="qrCode" :alt="checkout.isDemo ? 'Demo payment QR code' : 'QR code for Stripe Checkout'" />
          <template v-if="checkout.isDemo">
            <button :disabled="submittingPayment" type="button" @click="completeDemoPayment">
              {{ submittingPayment ? "Submitting…" : "Submit Payment" }}
            </button>
          </template>
          <template v-else>
            <a :href="checkout.checkoutURL" rel="noopener noreferrer" target="_blank">Open secure checkout</a>
            <button type="button" @click="copyLink">Copy payment link</button>
            <button :disabled="submitting || !submittedOrder" type="button" @click="refreshPaymentLink">Refresh payment link</button>
            <p>Waiting for verified payment…</p>
          </template>
        </section>
      </aside>
    </section>
  </main>
</template>
