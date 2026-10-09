<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="brand" to="/api/queue">BrewFlow</RouterLink>
      <nav aria-label="Primary navigation">
        <RouterLink to="/api/queue">Queue</RouterLink>
        <RouterLink to="/api/history">History</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>
