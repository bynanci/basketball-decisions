<script setup lang="ts">
defineProps<{ label: string; to: string }>()
</script>
<template>
  <RouterLink class="button-link recovery-action-link" :to="to">{{ label }}</RouterLink>
</template>
