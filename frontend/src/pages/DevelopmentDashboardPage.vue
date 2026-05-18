<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient, type DevelopmentDashboardPlayerSummary, type DevelopmentDashboardResponse } from '../api/client'

const router = useRouter()
const dashboard = ref<DevelopmentDashboardResponse | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')

const sortedPlayers = computed<DevelopmentDashboardPlayerSummary[]>(() =>
  [...(dashboard.value?.player_summaries ?? [])].sort((a, b) => {
    const aScore = a.player_value_score ?? -1
    const bScore = b.player_value_score ?? -1
    return bScore - aScore || a.project_id.localeCompare(b.project_id) || a.player_key.localeCompare(b.player_key)
  })
)

function formatDate(value?: string | null) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function formatNumber(value?: number | string | null) {
  if (value === null || value === undefined || value === '—') return '—'
  if (typeof value === 'string') return value
  return value.toFixed(2)
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}

function trendLabel(value?: number | null) {
  if (value === null || value === undefined) return 'No trend delta'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(2)}`
}

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    dashboard.value = await apiClient.getDevelopmentDashboard()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load development dashboard.'
  } finally {
    isLoading.value = false
  }
}

async function startWorkflowFromAction(actionId: string) {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const workflow = await apiClient.createWorkflowFromAction({ action_id: actionId })
    await router.push(`/workflows/${workflow.workflow_id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to start guided workflow.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page development-dashboard-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">M26 Dashboard</p>
        <h1>Development Progress Dashboard</h1>
        <p class="lede">
          Aggregates existing local artifacts into operational progress, health, and review summaries without changing scoring formulas, generating coaching advice, or claiming official scouting-grade evaluation; it is not an official scouting-grade evaluation.
        </p>
      </div>
      <button class="primary" :disabled="isLoading" @click="loadDashboard">
        {{ isLoading ? 'Refreshing…' : 'Refresh dashboard' }}
      </button>
    </header>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="muted">Loading development dashboard…</p>
    <p v-if="dashboard" class="muted">Generated {{ formatDate(dashboard.generated_at) }}</p>

    <div v-if="dashboard?.warnings.length" class="warning-card">
      <strong>Artifact warnings</strong>
      <ul>
        <li v-for="warning in dashboard.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </div>

    <section v-if="dashboard" class="metric-grid">
      <article v-for="metric in dashboard.metrics" :key="metric.key" class="card metric-card" :class="`metric-${metric.severity}`">
        <span class="metric-label">{{ metric.label }}</span>
        <strong>{{ formatNumber(metric.value) }}</strong>
        <span class="muted">{{ metric.detail }}</span>
      </article>
    </section>

    <div v-if="dashboard" class="grid two-column">
      <section class="card">
        <div class="section-header">
          <h2>Next-best-actions</h2>
          <span class="muted">Operational artifact follow-ups only</span>
        </div>
        <p v-if="!dashboard.next_best_actions.length" class="status">No blocking artifact follow-ups were detected.</p>
        <ul v-else class="action-list">
          <li v-for="action in dashboard.next_best_actions" :key="action.action_id" :class="`action-${action.severity}`">
            <strong>{{ action.title }}</strong>
            <p>{{ action.detail }}</p>
            <div class="button-row">
              <RouterLink v-if="action.href" :to="action.href" class="button-link">Open {{ action.artifact ?? 'artifact' }}</RouterLink>
              <button class="secondary" :disabled="isLoading" @click="startWorkflowFromAction(action.action_id)">Start guided workflow</button>
            </div>
          </li>
        </ul>
      </section>

      <section class="card">
        <h2>Team Summary</h2>
        <dl class="trace-list">
          <dt>Players</dt><dd>{{ dashboard.team_summary.player_count }}</dd>
          <dt>Avg Player Value</dt><dd>{{ formatNumber(dashboard.team_summary.average_player_value_score) }}</dd>
          <dt>Avg confidence</dt><dd>{{ formatPercent(dashboard.team_summary.average_confidence) }}</dd>
          <dt>Decision events</dt><dd>{{ dashboard.team_summary.total_decision_events }}</dd>
          <dt>Trend series</dt><dd>{{ dashboard.team_summary.trend_series_count }}</dd>
          <dt>Practice plans</dt><dd>{{ dashboard.team_summary.practice_plan_count }}</dd>
          <dt>Practice executions</dt><dd>{{ dashboard.team_summary.practice_execution_count }}</dd>
          <dt>Coach reports</dt><dd>{{ dashboard.team_summary.coach_report_count }}</dd>
        </dl>
        <ul class="muted">
          <li v-for="note in dashboard.team_summary.notes" :key="note">{{ note }}</li>
        </ul>
      </section>
    </div>

    <section v-if="dashboard" class="card">
      <div class="section-header">
        <h2>Player Development Table</h2>
        <RouterLink class="button-link" to="/player-value">Open Player Value</RouterLink>
      </div>
      <div v-if="sortedPlayers.length" class="table-card compact-table">
        <table>
          <thead>
            <tr>
              <th>Project</th>
              <th>Player</th>
              <th>Role</th>
              <th>Player Value</th>
              <th>Confidence</th>
              <th>Events</th>
              <th>Trend points</th>
              <th>Latest delta</th>
              <th>Warnings</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="player in sortedPlayers" :key="`${player.project_id}:${player.player_key}`">
              <td>{{ player.project_id }}</td>
              <td><strong>{{ player.display_name ?? player.player_key }}</strong><br /><code>{{ player.player_key }}</code></td>
              <td>{{ player.role_hint ?? player.team_side ?? '—' }}</td>
              <td>{{ formatNumber(player.player_value_score) }}</td>
              <td>{{ formatPercent(player.confidence) }}</td>
              <td>{{ player.decision_event_count }}</td>
              <td>{{ player.trend_points }}</td>
              <td>{{ trendLabel(player.latest_trend_delta) }}</td>
              <td>{{ player.warnings.length ? player.warnings.join('; ') : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-card">No player summaries are available yet. Missing artifacts appear as warnings and next-best-actions instead of crashes.</p>
    </section>

    <div v-if="dashboard" class="grid two-column">
      <section class="card">
        <h2>Practice Feedback Summary</h2>
        <dl class="trace-list">
          <dt>Signals</dt><dd>{{ dashboard.practice_feedback_summary.signal_count }}</dd>
          <dt>Action signals</dt><dd>{{ dashboard.practice_feedback_summary.action_signal_count }}</dd>
          <dt>Warning signals</dt><dd>{{ dashboard.practice_feedback_summary.warning_signal_count }}</dd>
          <dt>Avg completion</dt><dd>{{ formatPercent(dashboard.practice_feedback_summary.completion_rate_average) }}</dd>
          <dt>Skipped blocks</dt><dd>{{ dashboard.practice_feedback_summary.skipped_count }}</dd>
          <dt>Modified blocks</dt><dd>{{ dashboard.practice_feedback_summary.modified_count }}</dd>
          <dt>Latest signal</dt><dd>{{ formatDate(dashboard.practice_feedback_summary.latest_signal_at) }}</dd>
        </dl>
      </section>

      <section class="card">
        <h2>Data / Model Health Summary</h2>
        <dl class="trace-list">
          <dt>Dataset health</dt><dd>{{ dashboard.dataset_health_summary.available ? 'Available' : 'Needs export' }}</dd>
          <dt>Recognition samples</dt><dd>{{ dashboard.dataset_health_summary.recognition_sample_count }}</dd>
          <dt>Recognition warnings</dt><dd>{{ dashboard.dataset_health_summary.recognition_warning_count }}</dd>
          <dt>Decision samples</dt><dd>{{ dashboard.dataset_health_summary.decision_sample_count }}</dd>
          <dt>Decision warnings</dt><dd>{{ dashboard.dataset_health_summary.decision_warning_count }}</dd>
          <dt>Registered models</dt><dd>{{ dashboard.model_registry_summary.model_count }}</dd>
          <dt>Active model</dt><dd>{{ dashboard.model_registry_summary.active_version ?? 'None' }}</dd>
          <dt>Review queue</dt><dd>{{ dashboard.review_queue_summary.open_count }} open / {{ dashboard.review_queue_summary.high_priority_count }} high priority</dd>
        </dl>
      </section>
    </div>
  </section>
</template>
