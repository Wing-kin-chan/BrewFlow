import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/api/queue",
  },
  {
    path: "/api/queue",
    name: "queue",
    component: () => import("./pages/QueuePage.vue"),
  },
  {
    path: "/api/history",
    name: "history",
    component: () => import("./pages/OrderHistoryPage.vue"),
  },
  {
    path: "/api/pos",
    name: "pos",
    component: () => import("./pages/PosPage.vue"),
  },
  {
    path: "/api/receipt",
    name: "receipt",
    component: () => import("./pages/ReceiptPage.vue"),
  },
  {
    path: "/api/configuration",
    name: "configuration",
    component: () => import("./pages/ConfigurationPage.vue"),
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
