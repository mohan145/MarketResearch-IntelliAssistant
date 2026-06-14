<template>
  <div class="page page-centered">
    <div class="auth-card">
      <h1>Sign In</h1>
      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required autocomplete="email" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? "Signing in..." : "Sign In" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api";

const router = useRouter();
const email = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function handleSubmit(): Promise<void> {
  error.value = "";
  loading.value = true;
  try {
    const { access_token } = await login(email.value, password.value);
    localStorage.setItem("token", access_token);
    router.push("/");
  } catch {
    error.value = "Invalid email or password.";
  } finally {
    loading.value = false;
  }
}
</script>