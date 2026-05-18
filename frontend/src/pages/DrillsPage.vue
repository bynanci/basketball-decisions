<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, isApiClientError, type DrillCatalogItem, type DrillRecommendationResponse, type PracticeFeedbackSignal } from '../api/client'

const catalog = ref<DrillCatalogItem[]>([])
const latest = ref<DrillRecommendationResponse | null>(null)
const feedbackSignals = ref<PracticeFeedbackSignal[]>([])
const projectId = ref('')
const playerKey = ref('')
const maxRecommendations = ref(8)
const includePracticeFeedback = ref(true)
const feedbackLookbackLimit = ref(25)
const isLoading = ref(false)
const isBuilding = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')

const recommendations = computed(() => latest.value?.recommendations ?? [])
const recentFeedbackSignals = computed(() => feedbackSignals.value.slice(0, 8))

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

function priorityClass(priority: string) {
  return `priority priority-${priority.toLowerCase()}`
}

async function loadCatalog() {
  const response = await apiClient.listDrillCatalog()
  catalog.value = response.drills
}

async function loadFeedbackSignals() {
  const response = await apiClient.listDrillFeedbackSignals()
  feedbackSignals.value = response.signals
}

async function loadLatest() {
  try {
    latest.value = await apiClient.getLatestDrillRecommendations()
  } catch (error) {
    if (isApiClientError(error) && error.code === 'DRILL_RECOMMENDATIONS_NOT_FOUND') {
      latest.value = null
      return
    }
    throw error
  }
}

async function refresh() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    await loadCatalog()
    await loadLatest()
    await loadFeedbackSignals()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load drill recommendations.'
  } finally {
    isLoading.value = false
  }
}

async function buildRecommendations() {
  isBuilding.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    latest.value = await apiClient.buildDrillRecommendations({
      project_id: projectId.value.trim() || null,
      player_key: playerKey.value.trim() || null,
      max_recommendations: maxRecommendations.value,
      include_practice_feedback: includePracticeFeedback.value,
      feedback_lookback_limit: feedbackLookbackLimit.value
    })
    await loadFeedbackSignals()
    statusMessage.value = `Saved ${latest.value.recommendations.length} local drill recommendations.`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to build drill recommendations.'
  } finally {
    isBuilding.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="page drills-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">M22 Recommendation Engine</p>
        <h1>Drill Recommendations</h1>
        <p class="lede">
          Generate deterministic recommendations from diagnostics, Player Value, trends, teaching cases, and review findings using only the local drill catalog.
        </p>
      </div>
      <div class="button-row">
        <button class="ghost" :disabled="isLoading" @click="refresh">{{ isLoading ? 'Refreshing…' : 'Refresh' }}</button>
        <button class="primary" :disabled="isBuilding" @click="buildRecommendations">{{ isBuilding ? 'Generating…' : 'Generate recommendations' }}</button>
      </div>
    </header>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

    <section class="card">
      <h2>Filters</h2>
      <div class="form-grid three-column">
        <label>
          Project filter
          <input v-model="projectId" type="text" placeholder="Optional project_id" />
        </label>
        <label>
          Player alias filter
          <input v-model="playerKey" type="text" placeholder="Optional player_key" />
        </label>
        <label>
          Max cards
          <input v-model.number="maxRecommendations" type="number" min="1" max="24" />
        </label>
        <label class="checkbox-label">
          <input v-model="includePracticeFeedback" type="checkbox" />
          Use practice feedback
        </label>
        <label>
          Feedback lookback limit
          <input v-model.number="feedbackLookbackLimit" type="number" min="1" max="200" />
        </label>
      </div>
      <p class="muted">
        Coaching cues and success metrics are copied from the local catalog. The engine does not generate medical advice, injury advice, certification claims, or a practice calendar.
      </p>
    </section>

    <section class="recommendation-grid">
      <article v-for="recommendation in recommendations" :key="recommendation.recommendation_id" class="card recommendation-card">
        <div class="section-header">
          <div>
            <span :class="priorityClass(recommendation.priority)">{{ recommendation.priority }}</span>
            <h2>{{ recommendation.title }}</h2>
          </div>
          <div class="badge-stack">
            <strong>{{ formatPercent(recommendation.confidence) }} confidence</strong>
            <span v-if="recommendation.feedback_adjusted" class="feedback-badge">Feedback adjusted</span>
          </div>
        </div>
        <dl class="meta-grid">
          <div><dt>Role</dt><dd>{{ recommendation.role || 'Any role' }}</dd></div>
          <div><dt>Situation</dt><dd>{{ recommendation.situation }}</dd></div>
        </dl>
        <p>{{ recommendation.reason }}</p>
        <div class="list-columns">
          <div>
            <h3>Coaching cues</h3>
            <ul>
              <li v-for="cue in recommendation.coaching_cues" :key="cue">{{ cue }}</li>
            </ul>
          </div>
          <div>
            <h3>Success metrics</h3>
            <ul>
              <li v-for="metric in recommendation.success_metrics" :key="metric">{{ metric }}</li>
            </ul>
          </div>
        </div>
        <div v-if="recommendation.adjustment_summary.length" class="adjustment-panel">
          <h3>Practice feedback adjustments</h3>
          <ul>
            <li v-for="reason in recommendation.adjustment_summary" :key="reason">{{ reason }}</li>
          </ul>
        </div>
        <h3>Evidence refs</h3>
        <ul class="evidence-list">
          <li v-for="ref in recommendation.evidence_refs" :key="`${ref.source}-${ref.ref_id}-${ref.detail}`">
            <strong>{{ ref.source }}</strong>
            <span>{{ ref.ref_id || ref.prompt_id || ref.player_key || 'artifact' }}</span>
            <small>{{ ref.detail }}</small>
          </li>
        </ul>
      </article>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Recent feedback signals</h2>
        <span class="muted">{{ latest?.feedback_signal_count ?? feedbackSignals.length }} considered</span>
      </div>
      <p v-if="latest?.adjustment_summary.length" class="muted">{{ latest.adjustment_summary.join(' ') }}</p>
      <ul v-if="recentFeedbackSignals.length" class="evidence-list">
        <li v-for="signal in recentFeedbackSignals" :key="signal.signal_id || `${signal.signal_type}-${signal.execution_id}-${signal.reason}`">
          <strong>{{ signal.signal_type }}</strong>
          <span>{{ signal.drill_id || signal.recommendation_id || signal.execution_id }}</span>
          <small>{{ signal.reason }}</small>
        </li>
      </ul>
      <p v-else class="muted">No practice feedback signals have been saved yet.</p>
    </section>

    <section v-if="latest && !recommendations.length" class="card empty-state">
      <h2>No recommendations matched</h2>
      <p class="muted">The latest run completed, but no local artifact signals crossed the deterministic thresholds for the selected filters.</p>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Local catalog</h2>
        <span class="muted">{{ catalog.length }} drills</span>
      </div>
      <div class="catalog-list">
        <article v-for="drill in catalog" :key="drill.drill_id" class="catalog-item">
          <h3>{{ drill.title }}</h3>
          <p>{{ drill.role || 'Any role' }} · {{ drill.situation }}</p>
          <small>{{ drill.description }}</small>
        </article>
      </div>
    </section>
  </section>
</template>
