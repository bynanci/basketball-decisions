<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, ApiClientError, type RecognitionEvaluationReportRegistry, type RecognitionModelComparison, type RecognitionModelRegistry } from '../api/client'

const registry = ref<RecognitionModelRegistry | null>(null)
const reports = ref<RecognitionEvaluationReportRegistry | null>(null)
const comparison = ref<RecognitionModelComparison | null>(null)
const isLoading = ref(false)
const isTraining = ref(false)
const isActivating = ref<string | null>(null)
const isComparing = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const baseVersion = ref('')
const candidateVersion = ref('')

const sortedModels = computed(() => [...(registry.value?.models ?? [])].sort((a, b) => b.version.localeCompare(a.version)))

function showError(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    errorMessage.value = `${fallback} ${error.message}${error.debug_hint ? ` Hint: ${error.debug_hint}` : ''}`
  } else if (error instanceof Error) {
    errorMessage.value = `${fallback} ${error.message}`
  } else {
    errorMessage.value = fallback
  }
}

async function loadRegistry() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [registryResponse, reportResponse] = await Promise.all([
      apiClient.getRecognitionModelRegistry(),
      apiClient.getRecognitionEvaluationReports()
    ])
    registry.value = registryResponse
    reports.value = reportResponse
    baseVersion.value ||= registryResponse.active_version ?? registryResponse.models[0]?.version ?? ''
    candidateVersion.value ||= registryResponse.models.find((model) => model.version !== baseVersion.value)?.version ?? registryResponse.models[0]?.version ?? ''
  } catch (error) {
    showError(error, 'Could not load recognition model registry.')
  } finally {
    isLoading.value = false
  }
}

async function trainDraftModel() {
  isTraining.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const model = await apiClient.trainRecognitionBaseline(false)
    successMessage.value = `Trained immutable draft ${model.version}. It was not activated.`
    await loadRegistry()
  } catch (error) {
    showError(error, 'Could not train recognition baseline.')
  } finally {
    isTraining.value = false
  }
}

async function activate(version: string) {
  isActivating.value = version
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await apiClient.activateRecognitionModel(version, 'Manual activation from model registry page')
    registry.value = response.registry
    successMessage.value = `Activated ${response.active_version}; previous active model was ${response.previous_active_version ?? 'none'}.`
  } catch (error) {
    showError(error, `Could not activate ${version}.`)
  } finally {
    isActivating.value = null
  }
}

async function compare() {
  if (!baseVersion.value || !candidateVersion.value) return
  isComparing.value = true
  errorMessage.value = ''
  try {
    comparison.value = await apiClient.compareRecognitionModels(baseVersion.value, candidateVersion.value)
  } catch (error) {
    showError(error, 'Could not compare recognition models.')
  } finally {
    isComparing.value = false
  }
}

function formatMetric(value?: number | null) {
  if (value === undefined || value === null) return '—'
  return value.toFixed(3)
}

function shortHash(value?: string | null) {
  return value ? value.slice(0, 12) : '—'
}

onMounted(loadRegistry)
</script>

<template>
  <section class="page-stack">
    <div class="page-header">
      <div>
        <p class="eyebrow">Recognition Governance</p>
        <h1>Model Registry</h1>
        <p class="muted">Immutable local recognition model versions, explicit activation, rollback, dataset lineage, and evaluation reports.</p>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="isLoading" @click="loadRegistry">Refresh</button>
        <button type="button" :disabled="isTraining" @click="trainDraftModel">Train draft model</button>
      </div>
    </div>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success">{{ successMessage }}</p>

    <section class="card">
      <h2>Active recognition model</h2>
      <p class="status-line">Active version: <strong>{{ registry?.active_version ?? 'None' }}</strong></p>
      <p class="muted">Training creates the next v### folder and never promotes it unless activation is requested explicitly.</p>
    </section>

    <section class="card">
      <h2>Registered versions</h2>
      <div v-if="sortedModels.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Version</th>
              <th>Status</th>
              <th>F1</th>
              <th>Accuracy</th>
              <th>Dataset fingerprint</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in sortedModels" :key="model.version">
              <td>{{ model.version }}</td>
              <td>{{ model.active ? 'Active' : 'Draft / rollback target' }}</td>
              <td>{{ formatMetric(model.metrics?.f1) }}</td>
              <td>{{ formatMetric(model.metrics?.accuracy) }}</td>
              <td><code>{{ shortHash(model.dataset_fingerprint) }}</code></td>
              <td>{{ new Date(model.created_at).toLocaleString() }}</td>
              <td>
                <button type="button" :disabled="model.active || isActivating === model.version" @click="activate(model.version)">
                  {{ model.active ? 'Active' : 'Activate / rollback' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="muted">No recognition models have been trained yet.</p>
    </section>

    <section class="card comparison-card">
      <h2>Compare models</h2>
      <div class="comparison-controls">
        <label>Base
          <select v-model="baseVersion">
            <option v-for="model in registry?.models ?? []" :key="model.version" :value="model.version">{{ model.version }}</option>
          </select>
        </label>
        <label>Candidate
          <select v-model="candidateVersion">
            <option v-for="model in registry?.models ?? []" :key="model.version" :value="model.version">{{ model.version }}</option>
          </select>
        </label>
        <button type="button" :disabled="isComparing || !baseVersion || !candidateVersion" @click="compare">Compare</button>
      </div>
      <dl v-if="comparison" class="metric-grid">
        <div v-for="(delta, metric) in comparison.metric_deltas" :key="metric">
          <dt>{{ metric }}</dt>
          <dd>{{ delta > 0 ? '+' : '' }}{{ delta.toFixed(metric.includes('count') ? 0 : 3) }}</dd>
        </div>
      </dl>
    </section>

    <section class="card">
      <h2>Evaluation report registry</h2>
      <ul v-if="reports?.reports.length" class="report-list">
        <li v-for="report in reports.reports" :key="report.report_id">
          <strong>{{ report.model_version }}</strong> — F1 {{ formatMetric(report.metrics.f1) }}, dataset <code>{{ shortHash(report.dataset_fingerprint) }}</code>
        </li>
      </ul>
      <p v-else class="muted">No evaluation reports have been registered yet.</p>
    </section>
  </section>
</template>
