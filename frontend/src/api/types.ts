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

export interface CatalogItem {
  id: string;
  name: string;
  priceMinor: number;
  milkVolume: number;
  shots: number;
  texture: Texture | null;
}

export interface Catalog {
  currency: "gbp";
  group: "Drinks";
  items: CatalogItem[];
  milks: string[];
  textures: Texture[];
  options: string[];
  milkSurchargesMinor: Record<string, number>;
}

export interface PosOrderItemInput {
  identifier: string;
  catalogItemID: string;
  milk: string;
  texture: Texture | null;
  temperature: Temperature;
  options: string[];
}

export interface PosOrderInput {
  orderID: string;
  customer: string | null;
  items: PosOrderItemInput[];
}

export interface PricedItem extends PosOrderItemInput {
  name: string;
  unitAmountMinor: number;
}

interface CheckoutResponseBase {
  orderID: string;
  status: "pending_payment" | "paid" | "queued";
  currency: "gbp";
  totalMinor: number;
  items: PricedItem[];
}

export type CheckoutResponse = CheckoutResponseBase &
  (
    | {
        isDemo: false;
        demoBlocked: false;
        stripeSessionID: string;
        checkoutURL: string;
      }
    | {
        isDemo: true;
        demoBlocked: boolean;
        stripeSessionID: null;
        checkoutURL: null;
      }
  );

export interface Receipt {
  orderID: string;
  customer: string;
  status: "pending_payment" | "paid" | "queued";
  checkoutStatus: "creating" | "open" | "paid" | "expired" | "failed";
  currency: "gbp";
  totalMinor: number;
  items: PricedItem[];
  createdAt: string;
  paidAt: string | null;
  queuedAt: string | null;
  isDemo: boolean;
  demoBlocked: boolean;
}

export interface DemoModeConfiguration {
  demoModeEnabled: boolean;
  demoModePersisted: boolean;
  demoModeAvailable: boolean;
}
