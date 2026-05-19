<script setup lang="ts">
const props = defineProps<{
  type: 'empty' | 'error' | 'warning'
  title: string
  message: string
  actionLabel?: string
  actionTo?: string
}>()
</script>

<template>
  <div class="state-panel" :class="`state-${props.type}`">
    <strong>{{ props.title }}</strong>
    <p>{{ props.message }}</p>
    <RouterLink v-if="props.actionLabel && props.actionTo" class="button-link" :to="props.actionTo">{{ props.actionLabel }}</RouterLink>
  </div>
</template>
