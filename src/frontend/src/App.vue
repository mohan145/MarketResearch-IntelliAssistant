<template>
  <header class="navbar">
    <div class="navbar-brand">Market Intel Assistant</div>
    <nav class="navbar-links">
      <RouterLink to="/">New Research</RouterLink>
      <RouterLink to="/history">History</RouterLink>
      <RouterLink v-if="!isLoggedIn" to="/login">Login</RouterLink>
      <button v-else class="btn-link" @click="logout">Logout</button>
    </nav>
  </header>

  <main class="main-content">
    <RouterView />
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const isLoggedIn = computed(() => !!localStorage.getItem("token"));

function logout(): void {
  localStorage.removeItem("token");
  router.push("/login");
}
</script>