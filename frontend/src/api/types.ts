export type Temperature = "Warm" | "Normal" | "Extra Hot";
export type Texture = "Extra Wet" | "Wet" | "Dry" | "Extra Dry";

export interface Drink {
  orderID: string;
  drink: string;
  milk: string;
  milk_volume: number;
  shots: number;
  temperature: Temperature;
  texture: Texture | null;
  options: string[];
  customer: string;
  identifier: string;
  timeReceived: string | null;
  timeComplete: string | null;
}

export interface OrderQueueItem {
  kind: "order";
  orderID: string;
  customer: string;
  timeReceived: string | null;
  drinks: Drink[];
}

export interface BatchQueueItem {
  kind: "batch";
  milk: string;
  texture: Texture;
  volume: number;
  drinks: Drink[];
}

export type QueueItem = OrderQueueItem | BatchQueueItem;

export interface QueueSnapshot {
  revision: number;
  items: QueueItem[];
  totalOrders: number;
  totalDrinks: number;
}

export interface CompletedOrder {
  orderID: string;
  customer: string;
  dateReceived: string | null;
  timeReceived: string | null;
  timeComplete: string | null;
  drinks: Drink[];
}

export interface HistorySnapshot {
  revision: number;
  orders: CompletedOrder[];
  totalOrders: number;
  totalDrinks: number;
}
