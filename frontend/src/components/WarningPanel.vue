<script setup lang="ts">
defineProps<{ title: string; warnings: string[]; actionLabel?: string; actionTo?: string }>()
</script>
<template>
  <div class="state-panel state-warning">
    <strong>{{ title }}</strong>
    <ul>
      <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
    </ul>
    <RouterLink v-if="actionLabel && actionTo" class="button-link" :to="actionTo">{{ actionLabel }}</RouterLink>
  </div>
</template>
