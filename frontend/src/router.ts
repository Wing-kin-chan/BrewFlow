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
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
