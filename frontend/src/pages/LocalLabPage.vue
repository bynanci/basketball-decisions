<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  apiClient,
  type DatasetManifest,
  type DatasetSummary,
  type DecisionEventsBuildSummary,
  type LocalLabProjectArtifact,
  type VideoSourceRecord,
  isApiClientError
} from '../api/client'

const projects = ref<LocalLabProjectArtifact[]>([])
const datasets = ref<DatasetSummary[]>([])
const sourceRegistry = ref<VideoSourceRecord[]>([])
const isLoading = ref(false)
const isExportingRecognition = ref(false)
const isExportingDecision = ref(false)
const isBuildingDecisionEvents = ref(false)
const isSeedingSources = ref(false)
const isCuratingRecognition = ref(false)
const isCuratingDecision = ref(false)
const decisionEventsSummary = ref<DecisionEventsBuildSummary | null>(null)
const lastExportManifest = ref<DatasetManifest | null>(null)
const statusMessage = ref('')
const errorMessage = ref('')
const errorCode = ref('')

const sortedDatasets = computed(() => [...datasets.value].sort((a, b) => a.dataset_type.localeCompare(b.dataset_type)))

function boolLabel(value: boolean) {
  return value ? 'Yes' : 'No'
}

function formatDate(value?: string | null) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)
}

function formatRatio(value?: number | null) {
  if (value === null || value === undefined) return '—'
  return `${formatNumber(value)}:1`
}

function hasFewNegatives(dataset: DatasetSummary | DatasetManifest) {
  return dataset.positive_sample_count > 0 && dataset.negative_sample_count < Math.max(1, Math.ceil(dataset.positive_sample_count / 10))
}

function hasImbalance(dataset: DatasetSummary | DatasetManifest) {
  return dataset.negative_sample_count === 0 ? dataset.positive_sample_count > 0 : dataset.positive_sample_count / dataset.negative_sample_count > 5
}

function formatLabelDistribution(distribution: Record<string, number>) {
  const entries = Object.entries(distribution)
  if (!entries.length) return 'No labels yet'
  return entries.map(([label, count]) => `${label}: ${count}`).join(', ')
}

function datasetTitle(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function showError(error: unknown, fallback: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
  } else {
    errorCode.value = 'FRONTEND_ERROR'
    errorMessage.value = error instanceof Error ? error.message : fallback
  }
}

async function refreshLocalLab() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [projectResponse, datasetResponse, sourceResponse] = await Promise.all([apiClient.listLocalLabProjects(), apiClient.listDatasets(), apiClient.listSources()])
    projects.value = projectResponse.projects
    datasets.value = datasetResponse.datasets
    sourceRegistry.value = sourceResponse
  } catch (error) {
    showError(error, 'Could not load the Local Lab registry.')
  } finally {
    isLoading.value = false
  }
}

async function exportRecognitionDataset() {
  isExportingRecognition.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const manifest = await apiClient.exportRecognitionDataset()
    lastExportManifest.value = manifest
    statusMessage.value = `Recognition dataset exported with ${manifest.sample_count} samples and ${manifest.label_count} labels. Included ${manifest.included_project_count} projects; skipped ${manifest.skipped_project_count}.`
    await refreshLocalLab()
  } catch (error) {
    showError(error, 'Could not export the recognition dataset.')
  } finally {
    isExportingRecognition.value = false
  }
}

async function exportDecisionDataset() {
  isExportingDecision.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const manifest = await apiClient.exportDecisionDataset()
    lastExportManifest.value = manifest
    statusMessage.value = `Decision dataset exported with ${manifest.sample_count} samples and ${manifest.label_count} labels. Included ${manifest.included_project_count} projects; skipped ${manifest.skipped_project_count}.`
    await refreshLocalLab()
  } catch (error) {
    showError(error, 'Could not export the decision dataset.')
  } finally {
    isExportingDecision.value = false
  }
}


async function curateRecognitionDataset() {
  isCuratingRecognition.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const manifest = await apiClient.curateRecognitionDataset()
    lastExportManifest.value = manifest
    statusMessage.value = `Recognition dataset curated with ${manifest.positive_sample_count} positive samples and ${manifest.negative_sample_count} negative samples.`
    await refreshLocalLab()
  } catch (error) {
    showError(error, 'Could not curate the recognition dataset.')
  } finally {
    isCuratingRecognition.value = false
  }
}

async function curateDecisionDataset() {
  isCuratingDecision.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const manifest = await apiClient.curateDecisionDataset()
    lastExportManifest.value = manifest
    statusMessage.value = `Decision dataset curated with ${manifest.positive_sample_count} positive samples and ${manifest.negative_sample_count} negative samples.`
    await refreshLocalLab()
  } catch (error) {
    showError(error, 'Could not curate the decision dataset.')
  } finally {
    isCuratingDecision.value = false
  }
}

async function buildDecisionEvents() {
  isBuildingDecisionEvents.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const summary = await apiClient.buildDecisionEvents()
    decisionEventsSummary.value = summary
    statusMessage.value = `Built ${summary.event_count} explainable decision events.`
  } catch (error) {
    showError(error, 'Could not build decision events.')
  } finally {
    isBuildingDecisionEvents.value = false
  }
}

async function seedCandidateSources() {
  isSeedingSources.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    sourceRegistry.value = await apiClient.seedCandidateSources()
    statusMessage.value = `Seeded ${sourceRegistry.value.length} candidate source records. No media was downloaded.`
  } catch (error) {
    showError(error, 'Could not seed candidate source registry.')
  } finally {
    isSeedingSources.value = false
  }
}

onMounted(refreshLocalLab)
</script>

<template>
  <section class="card local-lab-hero">
    <p class="eyebrow">Local Lab</p>
    <h1>Local data memory layer</h1>
    <p>
      Review saved project artifacts, export JSONL datasets for future local ML training, and build local rule-based decision events. No cloud
      sync, database, learned model training, or learned player value scoring is run from this page.
    </p>
    <div class="button-row">
      <button type="button" :disabled="isExportingRecognition" @click="exportRecognitionDataset">
        {{ isExportingRecognition ? 'Exporting…' : 'Export Recognition Dataset' }}
      </button>
      <button type="button" :disabled="isExportingDecision" @click="exportDecisionDataset">
        {{ isExportingDecision ? 'Exporting…' : 'Export Decision Dataset' }}
      </button>
      <button type="button" :disabled="isCuratingRecognition" @click="curateRecognitionDataset">
        {{ isCuratingRecognition ? 'Curating…' : 'Curate Recognition Dataset' }}
      </button>
      <button type="button" :disabled="isCuratingDecision" @click="curateDecisionDataset">
        {{ isCuratingDecision ? 'Curating…' : 'Curate Decision Dataset' }}
      </button>
      <button type="button" :disabled="isBuildingDecisionEvents" @click="buildDecisionEvents">
        {{ isBuildingDecisionEvents ? 'Building…' : 'Build Decision Events' }}
      </button>
      <button type="button" :disabled="isSeedingSources" @click="seedCandidateSources">
        {{ isSeedingSources ? 'Seeding…' : 'Seed Candidate Sources' }}
      </button>
      <button class="secondary" type="button" :disabled="isLoading" @click="refreshLocalLab">Refresh</button>
    </div>
    <p v-if="statusMessage" class="success-message">{{ statusMessage }}</p>

    <div v-if="lastExportManifest" class="export-summary">
      <strong>Last export summary</strong>
      <p>{{ datasetTitle(lastExportManifest.dataset_type) }} included {{ lastExportManifest.included_project_count }} projects and skipped {{ lastExportManifest.skipped_project_count }}.</p>
      <dl class="curation-metrics">
        <div><dt>Positive</dt><dd>{{ lastExportManifest.positive_sample_count }}</dd></div>
        <div><dt>Negative</dt><dd>{{ lastExportManifest.negative_sample_count }}</dd></div>
        <div><dt>Ratio</dt><dd>{{ formatRatio(lastExportManifest.positive_negative_ratio) }}</dd></div>
      </dl>
      <p><strong>Label distribution:</strong> {{ formatLabelDistribution(lastExportManifest.label_distribution) }}</p>
      <p v-if="hasFewNegatives(lastExportManifest)" class="warning-message">Negative samples are underrepresented. Add more tracking review exclusions or bad-decision prompts.</p>
      <p v-if="hasImbalance(lastExportManifest)" class="warning-message">Positive/negative sample imbalance is greater than 5:1.</p>
      <ul v-if="lastExportManifest.skipped_projects.length">
        <li v-for="project in lastExportManifest.skipped_projects" :key="project.project_id">
          <strong>{{ project.name ?? project.project_id }}</strong>: {{ project.reason }}
        </li>
      </ul>
    </div>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
    </div>
  </section>


  <section class="card">
    <div class="table-header">
      <div>
        <p class="eyebrow">Source Registry</p>
        <h2>Candidate source governance</h2>
      </div>
      <span>{{ sourceRegistry.length }} sources</span>
    </div>
    <p class="muted">Candidate entries are metadata only. Do not bulk-download league or YouTube highlights, and verify rights before importing datasets.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>License</th>
            <th>Usage</th>
            <th>Training</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in sourceRegistry" :key="source.source_id">
            <td><strong>{{ source.name }}</strong><small v-if="source.source_url">{{ source.source_url }}</small></td>
            <td>{{ source.source_type }}</td>
            <td>{{ source.license_type }}</td>
            <td>{{ source.usage_scope }}</td>
            <td>{{ boolLabel(source.allowed_for_training) }}</td>
            <td>{{ source.notes }}</td>
          </tr>
          <tr v-if="sourceRegistry.length === 0">
            <td colspan="6">No candidate sources seeded yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card decision-events-card">
    <div>
      <p class="eyebrow">Decision Engine v1</p>
      <h2>Explainable decision events</h2>
      <p>Build role-adjusted, rule-based events from saved quiz attempts and write them to the local player value dataset.</p>
    </div>
    <dl>
      <div>
        <dt>Event count</dt>
        <dd>{{ decisionEventsSummary ? decisionEventsSummary.event_count : 'Not built' }}</dd>
      </div>
      <div>
        <dt>Avg raw score</dt>
        <dd>{{ decisionEventsSummary ? formatNumber(decisionEventsSummary.avg_raw_score) : '—' }}</dd>
      </div>
      <div>
        <dt>Avg role adjusted score</dt>
        <dd>{{ decisionEventsSummary ? formatNumber(decisionEventsSummary.avg_role_adjusted_score) : '—' }}</dd>
      </div>
      <div>
        <dt>Avg opportunity cost</dt>
        <dd>{{ decisionEventsSummary ? formatNumber(decisionEventsSummary.opportunity_cost_avg) : '—' }}</dd>
      </div>
    </dl>
  </section>

  <section class="summary-grid">
    <article v-for="dataset in sortedDatasets" :key="dataset.dataset_type" class="card dataset-card">
      <p class="eyebrow">{{ datasetTitle(dataset.dataset_type) }}</p>
      <h2>{{ dataset.sample_count }} samples</h2>
      <dl>
        <div>
          <dt>Labels</dt>
          <dd>{{ dataset.label_count }}</dd>
        </div>
        <div>
          <dt>Projects</dt>
          <dd>{{ dataset.project_count }}</dd>
        </div>
        <div>
          <dt>Last exported</dt>
          <dd>{{ formatDate(dataset.last_exported_at) }}</dd>
        </div>
        <div>
          <dt>Positive</dt>
          <dd>{{ dataset.positive_sample_count }}</dd>
        </div>
        <div>
          <dt>Negative</dt>
          <dd>{{ dataset.negative_sample_count }}</dd>
        </div>
        <div>
          <dt>Pos/neg ratio</dt>
          <dd>{{ formatRatio(dataset.positive_negative_ratio) }}</dd>
        </div>
      </dl>
      <p class="label-distribution"><strong>Labels:</strong> {{ formatLabelDistribution(dataset.label_distribution) }}</p>
      <p v-if="hasFewNegatives(dataset)" class="warning-message">Negative samples are underrepresented. Add more tracking review exclusions or bad-decision prompts.</p>
      <p v-if="hasImbalance(dataset)" class="warning-message">Positive/negative sample imbalance is greater than 5:1.</p>
    </article>
  </section>

  <section class="card">
    <div class="table-header">
      <div>
        <p class="eyebrow">Project Artifact Index</p>
        <h2>Saved local projects</h2>
      </div>
      <span>{{ projects.length }} projects</span>
    </div>
    <p v-if="isLoading">Loading Local Lab registry…</p>
    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Project</th>
            <th>Video</th>
            <th>License</th>
            <th>Usage</th>
            <th>Training</th>
            <th>League</th>
            <th>Frames</th>
            <th>Calibration</th>
            <th>Tracking</th>
            <th>Review</th>
            <th>Cleaned</th>
            <th>Projected</th>
            <th>Prompts</th>
            <th>Attempts</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="project in projects" :key="project.project_id">
            <td>
              <strong>{{ project.name }}</strong>
              <small>{{ project.project_id }}</small>
            </td>
            <td>{{ boolLabel(project.has_video) }} <span v-if="project.source?.usage_scope === 'REFERENCE_ONLY'" class="warning-badge">Reference only</span></td>
            <td>{{ project.source?.license_type ?? 'Missing' }}</td>
            <td>{{ project.source?.usage_scope ?? 'Missing' }}</td>
            <td>{{ project.source ? boolLabel(project.source.allowed_for_training) : 'No' }}</td>
            <td>{{ project.source?.league_tag ?? 'UNKNOWN' }}</td>
            <td>{{ project.frame_count }}</td>
            <td>{{ boolLabel(project.has_calibration) }}</td>
            <td>{{ boolLabel(project.has_tracking) }}</td>
            <td>{{ boolLabel(project.has_tracking_review) }}</td>
            <td>{{ boolLabel(project.has_cleaned_tracking) }}</td>
            <td>{{ boolLabel(project.has_projected_tracks) }}</td>
            <td>{{ project.quiz_prompt_count }}</td>
            <td>{{ project.quiz_attempt_count }}</td>
            <td>{{ formatDate(project.updated_at) }}</td>
          </tr>
          <tr v-if="projects.length === 0">
            <td colspan="15">No local projects found yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>

.export-summary {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.85rem;
}

.warning-badge {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 999px;
  color: #92400e;
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  margin-left: 0.35rem;
  padding: 0.15rem 0.45rem;
}
.local-lab-hero {
  display: grid;
  gap: 1rem;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.success-message {
  color: #166534;
  font-weight: 700;
}

.warning-message {
  color: #92400e;
  font-weight: 800;
}

.curation-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
  margin: 0.75rem 0;
}

.curation-metrics dd {
  font-size: 1.25rem;
  font-weight: 800;
  margin: 0.25rem 0 0;
}

.label-distribution {
  color: #475569;
  font-size: 0.9rem;
}

.decision-events-card {
  display: grid;
  gap: 1rem;
}

.decision-events-card dl {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin: 0;
}

.decision-events-card div {
  min-width: 0;
}

.decision-events-card dt {
  color: #64748b;
}

.decision-events-card dd {
  font-size: 1.5rem;
  font-weight: 800;
  margin: 0.25rem 0 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.dataset-card dl {
  display: grid;
  gap: 0.6rem;
  margin: 1rem 0 0;
}

.dataset-card div,
.table-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.dataset-card dt {
  color: #64748b;
}

.dataset-card dd {
  margin: 0;
  font-weight: 700;
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.75rem;
  text-align: left;
  vertical-align: top;
}

td small {
  display: block;
  color: #64748b;
  margin-top: 0.25rem;
}
</style>
