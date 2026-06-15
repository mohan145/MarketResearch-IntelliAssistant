<template>
  <header class="navbar">
    <div class="navbar-brand">Market Intel Assistant</div>
    <nav class="navbar-links">
      <template v-if="isLoggedIn">
        <RouterLink to="/">New Research</RouterLink>
        <RouterLink to="/history">History</RouterLink>
        <button class="btn-link" @click="logout">Logout</button>
      </template>
      <RouterLink v-else to="/login">Login</RouterLink>
    </nav>
  </header>

  <main class="main-content">
    <RouterView />
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { logout } from "./api";

const router = useRouter();
const isLoggedIn = ref(!!localStorage.getItem("token"));

// Keep isLoggedIn in sync whenever the route changes (covers login + logout)
router.afterEach(() => {
  isLoggedIn.value = !!localStorage.getItem("token");
});
</script>