<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, isApiClientError, type ReviewQueueItem, type ReviewQueueItemType, type ReviewQueueStatus } from '../api/client'

const items = ref<ReviewQueueItem[]>([])
const isLoading = ref(false)
const isGenerating = ref(false)
const updatingItemId = ref<string | null>(null)
const statusMessage = ref('')
const errorMessage = ref('')

const typeLabels: Record<ReviewQueueItemType, string> = {
  RECOGNITION_TRACK: 'Recognition tracks',
  RECOGNITION_DETECTION: 'Recognition detections',
  DECISION_PROMPT: 'Decision prompts',
  DECISION_ATTEMPT: 'Decision attempts',
  PLAYER_VALUE_ATTRIBUTION: 'Player Value attribution',
  RULE_DRAFT: 'Rule drafts'
}

const typeOrder = Object.keys(typeLabels) as ReviewQueueItemType[]

const groupedItems = computed(() =>
  typeOrder
    .map((type) => ({ type, label: typeLabels[type], items: items.value.filter((item) => item.item_type === type) }))
    .filter((group) => group.items.length > 0)
)

const counts = computed(() => ({
  open: items.value.filter((item) => item.status === 'OPEN').length,
  resolved: items.value.filter((item) => item.status === 'RESOLVED').length,
  dismissed: items.value.filter((item) => item.status === 'DISMISSED').length
}))

function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function relatedLink(item: ReviewQueueItem) {
  if (item.item_type === 'RULE_DRAFT') return { to: '/decision-rules', label: 'Review rule draft' }
  if (item.item_type === 'PLAYER_VALUE_ATTRIBUTION' && item.project_id && item.player_key) {
    return { to: `/player-value/${encodeURIComponent(item.project_id)}/${encodeURIComponent(item.player_key)}`, label: 'Open Player Value evidence' }
  }
  if ((item.item_type === 'RECOGNITION_TRACK' || item.item_type === 'RECOGNITION_DETECTION') && item.project_id) {
    return { to: `/projects/${encodeURIComponent(item.project_id)}/tracking-review`, label: 'Open tracking review' }
  }
  if ((item.item_type === 'DECISION_PROMPT' || item.item_type === 'DECISION_ATTEMPT') && item.project_id) {
    return { to: `/projects/${encodeURIComponent(item.project_id)}/quiz-builder`, label: 'Open quiz builder' }
  }
  return { to: '/local-lab', label: 'Open Local Lab' }
}

async function loadQueue() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    items.value = await apiClient.listReviewQueue()
    statusMessage.value = items.value.length ? `Loaded ${items.value.length} review item(s).` : 'No review queue has been generated yet.'
  } catch (error) {
    if (isApiClientError(error)) errorMessage.value = `${error.code}: ${error.message}`
    else errorMessage.value = error instanceof Error ? error.message : 'Could not load review queue.'
  } finally {
    isLoading.value = false
  }
}

async function generateQueue() {
  isGenerating.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.generateReviewQueue()
    items.value = response.items
    statusMessage.value = `Generated ${response.generated_count} item(s): ${response.open_count} open, ${response.resolved_count} resolved, ${response.dismissed_count} dismissed.`
  } catch (error) {
    if (isApiClientError(error)) errorMessage.value = `${error.code}: ${error.message}`
    else errorMessage.value = error instanceof Error ? error.message : 'Could not generate review queue.'
  } finally {
    isGenerating.value = false
  }
}

async function updateItem(item: ReviewQueueItem, status: ReviewQueueStatus) {
  updatingItemId.value = item.item_id
  errorMessage.value = ''
  try {
    const updated = await apiClient.updateReviewQueueItem(item.item_id, status)
    items.value = items.value.map((candidate) => (candidate.item_id === updated.item_id ? updated : candidate))
    statusMessage.value = `${updated.item_id} marked ${updated.status.toLowerCase()}. Source artifacts were not changed.`
  } catch (error) {
    if (isApiClientError(error)) errorMessage.value = `${error.code}: ${error.message}`
    else errorMessage.value = error instanceof Error ? error.message : 'Could not update review item.'
  } finally {
    updatingItemId.value = null
  }
}

onMounted(loadQueue)
</script>

<template>
  <section class="page review-queue-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Active learning</p>
        <h1>Review Queue</h1>
        <p class="lede">
          Unified queue for uncertain recognition, decision diagnostics, high-cost attempts, Player Value attribution, and rule drafts.
        </p>
      </div>
      <button class="primary" :disabled="isGenerating" @click="generateQueue">
        {{ isGenerating ? 'Generating…' : 'Generate queue' }}
      </button>
    </header>

    <div class="metric-grid compact-metrics">
      <article class="metric-card"><strong>{{ counts.open }}</strong><span>Open</span></article>
      <article class="metric-card"><strong>{{ counts.resolved }}</strong><span>Resolved</span></article>
      <article class="metric-card"><strong>{{ counts.dismissed }}</strong><span>Dismissed</span></article>
    </div>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="muted">Loading review queue…</p>

    <div v-if="!isLoading && !items.length" class="empty-state">
      Generate the queue to collect open review work from existing diagnostics and local artifacts.
    </div>

    <section v-for="group in groupedItems" :key="group.type" class="card queue-group">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ group.type }}</p>
          <h2>{{ group.label }}</h2>
        </div>
        <span class="pill">{{ group.items.length }} item(s)</span>
      </div>

      <article v-for="item in group.items" :key="item.item_id" class="queue-item" :class="`status-${item.status.toLowerCase()}`">
        <div class="queue-item-header">
          <div>
            <span class="priority-badge" :class="`priority-${item.priority.toLowerCase()}`">{{ item.priority }}</span>
            <span class="status-pill">{{ item.status }}</span>
          </div>
          <small>Created {{ formatDate(item.created_at) }}</small>
        </div>

        <p class="queue-reason">{{ item.reason }}</p>
        <p><strong>Recommended action:</strong> {{ item.recommended_action }}</p>

        <dl class="metadata-list">
          <template v-if="item.project_id"><dt>Project</dt><dd><code>{{ item.project_id }}</code></dd></template>
          <template v-if="item.prompt_id"><dt>Prompt / draft</dt><dd><code>{{ item.prompt_id }}</code></dd></template>
          <template v-if="item.attempt_id"><dt>Attempt</dt><dd><code>{{ item.attempt_id }}</code></dd></template>
          <template v-if="item.track_id"><dt>Track</dt><dd><code>{{ item.track_id }}</code></dd></template>
          <template v-if="item.player_key"><dt>Player</dt><dd><code>{{ item.player_key }}</code></dd></template>
          <template v-if="item.resolved_at"><dt>Closed</dt><dd>{{ formatDate(item.resolved_at) }}</dd></template>
        </dl>

        <div class="queue-actions">
          <RouterLink class="button-link" :to="relatedLink(item).to">{{ relatedLink(item).label }}</RouterLink>
          <button class="ghost" :disabled="updatingItemId === item.item_id || item.status === 'RESOLVED'" @click="updateItem(item, 'RESOLVED')">Resolve</button>
          <button class="ghost" :disabled="updatingItemId === item.item_id || item.status === 'DISMISSED'" @click="updateItem(item, 'DISMISSED')">Dismiss</button>
          <button v-if="item.status !== 'OPEN'" class="ghost" :disabled="updatingItemId === item.item_id" @click="updateItem(item, 'OPEN')">Reopen</button>
        </div>
      </article>
    </section>
  </section>
</template>
