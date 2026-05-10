<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, type DatasetSummary, type LocalLabProjectArtifact, isApiClientError } from '../api/client'

const projects = ref<LocalLabProjectArtifact[]>([])
const datasets = ref<DatasetSummary[]>([])
const isLoading = ref(false)
const isExportingRecognition = ref(false)
const isExportingDecision = ref(false)
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
    const [projectResponse, datasetResponse] = await Promise.all([apiClient.listLocalLabProjects(), apiClient.listDatasets()])
    projects.value = projectResponse.projects
    datasets.value = datasetResponse.datasets
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
    statusMessage.value = `Recognition dataset exported with ${manifest.sample_count} samples and ${manifest.label_count} labels.`
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
    statusMessage.value = `Decision dataset exported with ${manifest.sample_count} samples and ${manifest.label_count} labels.`
    await refreshLocalLab()
  } catch (error) {
    showError(error, 'Could not export the decision dataset.')
  } finally {
    isExportingDecision.value = false
  }
}

onMounted(refreshLocalLab)
</script>

<template>
  <section class="card local-lab-hero">
    <p class="eyebrow">Local Lab</p>
    <h1>Local data memory layer</h1>
    <p>
      Review saved project artifacts and export JSONL datasets for future local ML training. No cloud sync, database, model training, or
      player value scoring is run from this page.
    </p>
    <div class="button-row">
      <button type="button" :disabled="isExportingRecognition" @click="exportRecognitionDataset">
        {{ isExportingRecognition ? 'Exporting…' : 'Export Recognition Dataset' }}
      </button>
      <button type="button" :disabled="isExportingDecision" @click="exportDecisionDataset">
        {{ isExportingDecision ? 'Exporting…' : 'Export Decision Dataset' }}
      </button>
      <button class="secondary" type="button" :disabled="isLoading" @click="refreshLocalLab">Refresh</button>
    </div>
    <p v-if="statusMessage" class="success-message">{{ statusMessage }}</p>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
    </div>
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
      </dl>
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
            <td>{{ boolLabel(project.has_video) }}</td>
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
            <td colspan="11">No local projects found yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
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
