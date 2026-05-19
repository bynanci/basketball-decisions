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
const expanded = ref(!acknowledged.value)

const resolvedStorageKey = computed(() => `${props.storageKey}:${props.surface}`)

function getStorage() {
  try {
    return window.localStorage
  } catch {
    try {
      return window.sessionStorage
    } catch {
      return null
    }
  }
}

function readStoredAck() {
  const storage = getStorage()
  if (!storage) return false
  return storage.getItem(`${props.storageKey}:${props.surface}`) === '1'
}

function acknowledge() {
  acknowledged.value = true
  expanded.value = false
  const storage = getStorage()
  storage?.setItem(resolvedStorageKey.value, '1')
}

function reopen() {
  expanded.value = true
}
</script>

<template>
  <aside class="trust-caveat" :class="{ compact }" :data-testid="`trust-caveat-${surface}`">
    <div v-if="!acknowledged || expanded" class="trust-caveat-panel" role="status" aria-live="polite">
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <button v-if="!acknowledged" class="primary" type="button" @click="acknowledge">I understand</button>
      <button v-else class="ghost" type="button" @click="expanded = false">Hide details</button>
    </div>
    <p v-else class="trust-caveat-badge">
      <strong>{{ title }} acknowledged.</strong>
      <span>{{ message }}</span>
      <button class="link-button" type="button" @click="reopen">Review caveat</button>
    </p>
  </aside>
</template>
