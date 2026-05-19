<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, type PracticeExecution, type PracticeExecutionBlockStatus, type PracticeFeedbackSummary } from '../api/client'
import TrustCaveatGate from '../components/TrustCaveatGate.vue'

const props = defineProps<{ executionId: string }>()

const execution = ref<PracticeExecution | null>(null)
const summary = ref<PracticeFeedbackSummary | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')

const statusOptions: PracticeExecutionBlockStatus[] = ['COMPLETED', 'SKIPPED', 'MODIFIED', 'INCOMPLETE']
const blocks = computed(() => execution.value?.blocks ?? [])

function percent(value: number) {
  return `${Math.round(value * 100)}%`
}

async function refresh() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    execution.value = await apiClient.getPracticeExecution(props.executionId)
    summary.value = await apiClient.getPracticeFeedbackSummary(props.executionId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load practice execution.'
  } finally {
    isLoading.value = false
  }
}

function normalizeNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

async function saveExecution() {
  if (!execution.value) return
  isSaving.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    execution.value = await apiClient.updatePracticeExecution(execution.value.execution_id, {
      started_by: execution.value.started_by,
      notes: execution.value.notes,
      completed_at: execution.value.completed_at,
      blocks: execution.value.blocks.map((block) => ({
        ...block,
        outcome_rating: normalizeNumber(block.outcome_rating),
        actual_duration_minutes: normalizeNumber(block.actual_duration_minutes)
      }))
    })
    summary.value = await apiClient.getPracticeFeedbackSummary(execution.value.execution_id)
    statusMessage.value = 'Saved execution feedback.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to save practice execution.'
  } finally {
    isSaving.value = false
  }
}

function markComplete() {
  if (!execution.value) return
  execution.value.completed_at = new Date().toISOString()
}

onMounted(refresh)
</script>

<template>
  <section class="page practice-execution-detail-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Execution Session</p>
        <h1>{{ execution?.plan_title || 'Practice execution' }}</h1>
        <p class="lede">Update block statuses, notes, metric results, ratings, and actual duration. The source practice plan remains unchanged.</p>
      </div>
      <div class="button-row">
        <RouterLink class="button secondary-button" to="/practice-executions">All Executions</RouterLink>
        <button class="ghost" :disabled="isLoading" @click="refresh">{{ isLoading ? 'Refreshing…' : 'Refresh' }}</button>
        <button class="secondary-button" :disabled="!execution" @click="markComplete">Mark session complete</button>
        <button class="primary" :disabled="isSaving || !execution" @click="saveExecution">{{ isSaving ? 'Saving…' : 'Save feedback' }}</button>
      </div>
    </header>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

    <TrustCaveatGate
      surface="practice-execution"
      compact
      storage-key="trust-caveat-practice-execution-detail"
      message="Practice feedback signals are decision-support cues based on local execution notes and available evidence. They should be reviewed by a coach or analyst before changing training priorities."
    />

    <section v-if="execution" class="card">
      <div class="section-header">
        <div>
          <h2>{{ execution.execution_id }}</h2>
          <p class="muted">Plan {{ execution.plan_id }} · {{ execution.planned_duration_minutes }} planned minutes</p>
        </div>
        <span v-if="execution.completed_at" class="priority">Completed</span>
      </div>
      <div class="form-grid three-column">
        <label>
          Started by
          <input v-model="execution.started_by" type="text" placeholder="Optional" />
        </label>
        <label class="wide-field">
          Session notes
          <input v-model="execution.notes" type="text" placeholder="Optional practice-level notes" />
        </label>
      </div>
    </section>

    <section v-if="summary" class="card">
      <div class="section-header">
        <h2>Feedback summary</h2>
        <span class="muted">{{ percent(summary.completion_rate) }} complete</span>
      </div>
      <dl class="meta-grid">
        <div><dt>Average rating</dt><dd>{{ summary.average_block_rating ?? 'Not rated' }}</dd></div>
        <div><dt>Met metrics</dt><dd>{{ summary.met_metrics.length }}</dd></div>
        <div><dt>Missed metrics</dt><dd>{{ summary.missed_metrics.length }}</dd></div>
        <div><dt>Skipped / modified</dt><dd>{{ summary.skipped_count }} / {{ summary.modified_count }}</dd></div>
        <div><dt>Actual duration</dt><dd>{{ summary.actual_duration_minutes }} minutes</dd></div>
      </dl>
      <h3>Recommended next actions</h3>
      <ul><li v-for="action in summary.recommended_next_actions" :key="action">{{ action }}</li></ul>
      <h3>Signals</h3>
      <ul class="evidence-list">
        <li v-for="signal in summary.signals" :key="`${signal.signal_type}-${signal.block_id}-${signal.reason}`">
          <strong>{{ signal.signal_type }}</strong><span>{{ signal.severity }}</span><small>{{ signal.reason }}</small>
        </li>
        <li v-if="!summary.signals.length" class="muted">No signals yet.</li>
      </ul>
    </section>

    <section class="recommendation-grid">
      <article v-for="block in blocks" :key="block.block_id" class="card recommendation-card">
        <div class="section-header">
          <div>
            <span class="priority">{{ block.block_type }}</span>
            <h2>{{ block.planned_start_minute }}–{{ block.planned_end_minute }} min · {{ block.title }}</h2>
          </div>
          <strong>{{ block.planned_duration_minutes }} planned min</strong>
        </div>
        <div class="form-grid three-column">
          <label>
            Status
            <select v-model="block.status">
              <option v-for="option in statusOptions" :key="option" :value="option">{{ option }}</option>
            </select>
          </label>
          <label>
            Outcome rating
            <input v-model.number="block.outcome_rating" type="number" min="1" max="5" placeholder="1-5" />
          </label>
          <label>
            Actual duration
            <input v-model.number="block.actual_duration_minutes" type="number" min="0" placeholder="Minutes" />
          </label>
          <label>
            Modified title
            <input v-model="block.modified_title" type="text" placeholder="Optional" />
          </label>
          <label class="wide-field">
            Coach notes
            <input v-model="block.coach_notes" type="text" placeholder="Coach observations" />
          </label>
          <label class="wide-field">
            Player notes
            <input v-model="block.player_notes" type="text" placeholder="Player feedback" />
          </label>
          <label class="wide-field">
            Modification notes
            <input v-model="block.modified_notes" type="text" placeholder="What changed from the plan?" />
          </label>
        </div>
        <h3>Metric results</h3>
        <div class="catalog-list">
          <div v-for="metric in block.metric_results" :key="`${block.block_id}-${metric.metric}`" class="catalog-item">
            <label class="checkbox-row"><input v-model="metric.met" type="checkbox" /> Met</label>
            <strong>{{ metric.metric }}</strong>
            <input v-model="metric.result" type="text" placeholder="Observed result" />
            <input v-model="metric.notes" type="text" placeholder="Metric notes" />
          </div>
        </div>
      </article>
    </section>
  </section>
</template>
