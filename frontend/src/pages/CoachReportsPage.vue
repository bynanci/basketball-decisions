<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, COACH_REPORT_SECTIONS, isApiClientError, type CoachReport, type CoachReportBuildRequest, type CoachReportDepth, type CoachReportListItem, type CoachReportSectionName, type EvidenceLockedSummaryResponse } from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'

const title = ref('Coach Report')
const projectId = ref('')
const playerKey = ref('')
const createdBy = ref('')
const notes = ref('')
const reportDepth = ref<CoachReportDepth>('FULL')
const selectedSections = ref<Set<CoachReportSectionName>>(new Set(COACH_REPORT_SECTIONS))
const history = ref<CoachReportListItem[]>([])
const currentReport = ref<CoachReport | null>(null)
const isLoading = ref(false)
const isBuilding = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const llmSummary = ref<EvidenceLockedSummaryResponse | null>(null)

const previewMarkdown = computed(() => currentReport.value?.markdown ?? 'Build or select a report to preview deterministic Markdown here.')

function formatDate(value?: string | null) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function toggleSection(section: CoachReportSectionName) {
  const next = new Set(selectedSections.value)
  if (next.has(section)) next.delete(section)
  else next.add(section)
  selectedSections.value = next
}

function buildPayload(): CoachReportBuildRequest {
  return {
    title: title.value.trim() || 'Coach Report',
    project_id: projectId.value.trim() || null,
    player_key: playerKey.value.trim() || null,
    created_by: createdBy.value.trim() || null,
    notes: notes.value.trim() || null,
    report_depth: reportDepth.value,
    sections: COACH_REPORT_SECTIONS.filter((section) => selectedSections.value.has(section))
  }
}

async function loadHistory() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.listCoachReports()
    history.value = response.reports
    if (!currentReport.value && response.reports.length) {
      await selectReport(response.reports[0].report_id)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load coach report history.'
  } finally {
    isLoading.value = false
  }
}

async function buildReport() {
  isBuilding.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    currentReport.value = await apiClient.buildCoachReport(buildPayload())
    statusMessage.value = `Built ${currentReport.value.title} with ${currentReport.value.warnings.length} warnings.`
    await loadHistory()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to build coach report.'
  } finally {
    isBuilding.value = false
  }
}

async function selectReport(reportId: string) {
  errorMessage.value = ''
  try {
    currentReport.value = await apiClient.getCoachReport(reportId)
  } catch (error) {
    if (isApiClientError(error) && error.code === 'COACH_REPORT_NOT_FOUND') {
      errorMessage.value = 'That report is no longer available on disk.'
    } else {
      errorMessage.value = error instanceof Error ? error.message : 'Unable to load coach report.'
    }
  }
}

async function rewriteCoachSummary() {
  if (!currentReport.value) return
  errorMessage.value = ''
  llmSummary.value = null
  try {
    llmSummary.value = await apiClient.createEvidenceLockedSummary({ report_id: currentReport.value.report_id, provider: 'mock', created_by: createdBy.value.trim() || null })
    statusMessage.value = 'Generated LLM-assisted wording (evidence-locked).'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to rewrite coach summary.'
  }
}

onMounted(loadHistory)
</script>

<template>
  <section class="page coach-report-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">M21 Export</p>
        <h1>Coach Report Export</h1>
        <p class="lede">
          Build deterministic Markdown and structured JSON from local Player Value, diagnostics, rules, review, and governance artifacts.
        </p>
      </div>
      <button class="primary" :disabled="isBuilding" @click="buildReport">
        {{ isBuilding ? 'Building…' : 'Build report' }}
      </button>
    </header>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <ErrorState v-if="errorMessage" title="Coach reports API error" :message="errorMessage" action-label="Open Development Dashboard" action-to="/development-dashboard" />

    <div class="grid two-column">
      <section class="card report-builder">
        <h2>Report builder</h2>
        <label>
          Title
          <input v-model="title" type="text" placeholder="Coach Report" />
        </label>
        <div class="form-grid">
          <label>
            Project filter
            <input v-model="projectId" type="text" placeholder="Optional project_id" />
          </label>
          <label>
            Player alias filter
            <input v-model="playerKey" type="text" placeholder="Optional local player_key" />
          </label>
        </div>
        <label>
          Report depth
          <select v-model="reportDepth">
            <option value="FULL">Full report</option>
            <option value="SUMMARY">Summary report</option>
          </select>
        </label>
        <label>
          Created by
          <input v-model="createdBy" type="text" placeholder="Optional local reviewer name" />
        </label>
        <label>
          Notes
          <textarea v-model="notes" rows="3" placeholder="Optional builder notes stored in methodology." />
        </label>
        <fieldset>
          <legend>Available sections</legend>
          <label v-for="section in COACH_REPORT_SECTIONS" :key="section" class="checkbox-row">
            <input type="checkbox" :checked="selectedSections.has(section)" @change="toggleSection(section)" />
            {{ section }}
          </label>
        </fieldset>
        <p class="muted">
          Missing artifacts are recorded as warnings, not crashes. PDF, DOCX, and email export are intentionally not implemented.
        </p>
      </section>

      <section class="card report-preview">
        <div class="section-header">
          <h2>Preview</h2>
          <div v-if="currentReport" class="button-row">
            <button class="ghost" @click="rewriteCoachSummary">Rewrite as coach-friendly summary</button>
            <a class="button-link" :href="apiClient.coachReportMarkdownUrl(currentReport.report_id)" target="_blank" rel="noreferrer">Markdown</a>
            <a class="button-link" :href="apiClient.coachReportJsonUrl(currentReport.report_id)" target="_blank" rel="noreferrer">JSON</a>
          </div>
        </div>
        <p v-if="currentReport" class="muted">
          {{ currentReport.report_id }} · {{ currentReport.report_depth }} · {{ formatDate(currentReport.created_at) }} · {{ currentReport.warnings.length }} warnings
        </p>
        <pre class="markdown-preview">{{ previewMarkdown }}</pre>
      </section>
    </div>

    <section v-if="llmSummary" class="card">
      <h2>LLM-assisted wording</h2>
      <p class="muted">LLM rewrite cannot change scores or evidence.</p>
      <pre class="markdown-preview">{{ llmSummary.llm_assisted_wording }}</pre>
      <p v-if="!llmSummary.validation.warnings_preserved || !llmSummary.validation.scores_unchanged || !llmSummary.validation.evidence_refs_preserved || llmSummary.validation.prohibited_phrases.length" class="warning-cell">
        Validation warning: warnings_preserved={{ llmSummary.validation.warnings_preserved }}, scores_unchanged={{ llmSummary.validation.scores_unchanged }}, evidence_refs_preserved={{ llmSummary.validation.evidence_refs_preserved }}, prohibited={{ llmSummary.validation.prohibited_phrases.join(', ') || 'none' }}
      </p>
    </section>

    <section class="card report-history">
      <div class="section-header">
        <h2>History</h2>
        <button class="ghost" :disabled="isLoading" @click="loadHistory">{{ isLoading ? 'Refreshing…' : 'Refresh' }}</button>
      </div>
      <EmptyState v-if="!history.length" title="No coach reports yet" message="Build your first report or load sample data." action-label="Load sample project" action-to="/" />
      <div v-else class="table-card compact-table">
        <table>
          <thead>
            <tr>
              <th>Report</th>
              <th>Generated</th>
              <th>Depth</th>
              <th>Filters</th>
              <th>Sections</th>
              <th>Warnings</th>
              <th>Downloads</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in history" :key="report.report_id">
              <td><button class="link-button" @click="selectReport(report.report_id)">{{ report.title }}</button><br /><span class="muted">{{ report.report_id }}</span></td>
              <td>{{ formatDate(report.created_at) }}</td>
              <td>{{ report.report_depth }}</td>
              <td>{{ report.project_id || 'All projects' }} / {{ report.player_key || 'All aliases' }}</td>
              <td>{{ report.section_names.join(', ') }}</td>
              <td>{{ report.warning_count }}</td>
              <td>
                <a :href="apiClient.coachReportMarkdownUrl(report.report_id)" target="_blank" rel="noreferrer">Markdown</a>
                ·
                <a :href="apiClient.coachReportJsonUrl(report.report_id)" target="_blank" rel="noreferrer">JSON</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
