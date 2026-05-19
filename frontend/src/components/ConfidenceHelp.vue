<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant: 'player' | 'coach' | 'analyst'
  compact?: boolean
}>(), {
  compact: false
})

const CORE_COPY = 'Confidence estimates how complete and reliable the local evidence is for this score. It can decrease when sample size is low, player identity is UNKNOWN, attribution is ambiguous, artifacts are stale, or model/data baselines differ.'
const PLAYER_COPY = 'Confidence shows how much local evidence supports this training signal. Low confidence means you should review warnings before acting on it.'

const variantCopy = computed(() => {
  if (props.variant === 'player') return PLAYER_COPY
  if (props.variant === 'coach') return `${CORE_COPY} Use this with coach judgment and review warnings before acting.`
  return `${CORE_COPY} Compare confidence with warning context before interpreting score differences.`
})
</script>

<template>
  <p class="confidence-help" :class="{ compact: props.compact }">
    {{ variantCopy }}
  </p>
</template>

<style scoped>
.confidence-help {
  margin: 0.5rem 0;
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.4;
}

.confidence-help.compact {
  margin: 0.25rem 0;
  font-size: 0.88rem;
}
</style>
