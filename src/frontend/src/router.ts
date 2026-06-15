import { createRouter, createWebHistory } from "vue-router";
import NewResearch from "./pages/NewResearch.vue";
import History from "./pages/History.vue";
import Login from "./pages/Login.vue";

const routes = [
  { path: "/", component: NewResearch, meta: { requiresAuth: true } },
  { path: "/history", component: History, meta: { requiresAuth: true } },
  { path: "/login", component: Login },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Auth guard — all requiresAuth routes redirect to /login if no token
router.beforeEach((to) => {
  const token = localStorage.getItem("token");
  if (to.meta.requiresAuth && !token) {
    return { path: "/login" };
  }
  // Already logged in, don't show login page again
  if (to.path === "/login" && token) {
    return { path: "/" };
  }
});

export default router;