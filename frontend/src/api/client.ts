import type {
  Catalog,
  CheckoutResponse,
  DemoModeConfiguration,
  HistorySnapshot,
  PosOrderInput,
  QueueSnapshot,
  Receipt,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Fall back to a status-only error for non-JSON responses.
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }
  return (await response.json()) as T;
}

export async function fetchQueue(): Promise<QueueSnapshot> {
  return responseJson<QueueSnapshot>(await fetch("/api/queue/state"));
}

export async function fetchHistory(): Promise<HistorySnapshot> {
  return responseJson<HistorySnapshot>(await fetch("/api/history/orders"));
}

export async function completeDrinks(drinkIDs: string[]): Promise<QueueSnapshot> {
  return responseJson<QueueSnapshot>(
    await fetch("/api/queue/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drinkIDs }),
    }),
  );
}

export async function fetchCatalog(): Promise<Catalog> {
  return responseJson<Catalog>(await fetch("/api/pos/catalog"));
}

export async function createCheckout(order: PosOrderInput): Promise<CheckoutResponse> {
  return responseJson<CheckoutResponse>(
    await fetch("/api/pos/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(order),
    }),
  );
}

export async function fetchReceipt(sessionID: string): Promise<Receipt> {
  return responseJson<Receipt>(
    await fetch(`/api/pos/receipts/${encodeURIComponent(sessionID)}`),
  );
}

export async function fetchDemoReceipt(orderID: string): Promise<Receipt> {
  return responseJson<Receipt>(
    await fetch(`/api/pos/demo-receipts/${encodeURIComponent(orderID)}`),
  );
}

export async function submitDemoPayment(orderID: string): Promise<Receipt> {
  return responseJson<Receipt>(
    await fetch(`/api/pos/orders/${encodeURIComponent(orderID)}/demo-payment`, {
      method: "POST",
    }),
  );
}

export async function fetchDemoMode(): Promise<DemoModeConfiguration> {
  return responseJson<DemoModeConfiguration>(await fetch("/api/configuration/demo-mode"));
}

export async function updateDemoMode(
  demoModeEnabled: boolean,
): Promise<DemoModeConfiguration> {
  return responseJson<DemoModeConfiguration>(
    await fetch("/api/configuration/demo-mode", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demoModeEnabled }),
    }),
  );
}
