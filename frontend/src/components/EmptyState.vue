<script setup lang="ts">
defineProps<{ title: string; message: string; actionLabel?: string; actionTo?: string }>()
</script>
<template>
  <div class="state-panel state-empty">
    <strong>{{ title }}</strong>
    <p>{{ message }}</p>
    <RouterLink v-if="actionLabel && actionTo" class="button-link" :to="actionTo">{{ actionLabel }}</RouterLink>
  </div>
</template>
