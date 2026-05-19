<script setup lang="ts">
import { computed, ref } from 'vue'

const DEFAULT_TITLE = 'Trust caveat'
const DEFAULT_MESSAGE = 'Court IQ outputs are decision-support signals based on local sample data, aliases, decision events, rules, and available evidence. Player Value is not an official scouting grade. Review confidence, warnings, and evidence before using recommendations.'

const props = withDefaults(defineProps<{
  surface: string
  compact?: boolean
  storageKey?: string
  title?: string
  message?: string
}>(), {
  compact: false,
  storageKey: 'court-iq-trust-caveat',
  title: DEFAULT_TITLE,
  message: DEFAULT_MESSAGE
})

const acknowledged = ref(readStoredAck())

const resolvedStorageKey = computed(() => `${props.storageKey}:${props.surface}`)

function getStorage() {
  try {
    return props.compact ? window.sessionStorage : window.localStorage
  } catch {
    return null
  }
}

function readStoredAck() {
  const storage = getStorage()
  if (!storage) return false
  return storage.getItem(`${props.storageKey}:${props.surface}`) === '1'
}

function acknowledge() {
  acknowledged.value = true
  const storage = getStorage()
  storage?.setItem(resolvedStorageKey.value, '1')
}
</script>

<template>
  <aside class="trust-caveat" :class="{ compact }" :data-testid="`trust-caveat-${surface}`">
    <div v-if="!acknowledged" class="trust-caveat-panel" role="status" aria-live="polite">
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <button class="primary" type="button" @click="acknowledge">I understand</button>
    </div>
    <p v-else class="trust-caveat-badge">
      <strong>{{ title }} acknowledged.</strong>
      <span>{{ message }}</span>
    </p>
  </aside>
</template>
