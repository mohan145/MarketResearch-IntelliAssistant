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

// Auth guard — disabled for Phase 0 testing, will be enforced in Phase 4
// router.beforeEach((to) => {
//   const token = localStorage.getItem("token");
//   if (to.meta.requiresAuth && !token) {
//     return { path: "/login" };
//   }
// });

export default router;