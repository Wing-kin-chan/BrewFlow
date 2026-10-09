import type { HistorySnapshot, QueueSnapshot } from "./types";

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
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
