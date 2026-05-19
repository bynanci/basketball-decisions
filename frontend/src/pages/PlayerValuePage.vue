<script setup lang="ts">
import TrustCaveatGate from '../components/TrustCaveatGate.vue'
import { onMounted, ref } from 'vue'
import { apiClient, isApiClientError, type PlayerValueBuildResponse, type PlayerValueSummary } from '../api/client'

const playerValue = ref<PlayerValueBuildResponse | null>(null)
const isLoading = ref(false)
const isBuilding = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')
const expandedKeys = ref<Set<string>>(new Set())

function rowKey(summary: PlayerValueSummary) {
  return `${summary.project_id}:${summary.player_key}`
}

function formatNumber(value: number, maximumFractionDigits = 2) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(value)
}

function formatPercent(value: number) {
  return `${formatNumber(value * 100)}%`
}

function formatDate(value?: string | null) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function toggle(summary: PlayerValueSummary) {
  const next = new Set(expandedKeys.value)
  const key = rowKey(summary)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedKeys.value = next
}

function describeWarnings(summary: PlayerValueSummary) {
  return summary.warnings.length ? summary.warnings.join(' | ') : '—'
}

async function loadPlayerValue() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    playerValue.value = await apiClient.getPlayerValue()
    statusMessage.value = `Loaded ${playerValue.value.summaries.length} Player Value summaries.`
  } catch (error) {
    if (isApiClientError(error) && error.code === 'PLAYER_VALUE_NOT_FOUND') {
      statusMessage.value = 'No Player Value summary has been built yet.'
      playerValue.value = null
    } else {
      errorMessage.value = error instanceof Error ? error.message : 'Unable to load Player Value summaries.'
    }
  } finally {
    isLoading.value = false
  }
}

async function buildPlayerValue() {
  isBuilding.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    playerValue.value = await apiClient.buildPlayerValue()
    expandedKeys.value = new Set()
    statusMessage.value = `Built ${playerValue.value.summaries.length} Player Value summaries.`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to build Player Value summaries.'
  } finally {
    isBuilding.value = false
  }
}

onMounted(loadPlayerValue)
</script>

<template>
  <section class="page player-value-page" data-testid="player-value-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Local Lab</p>
        <h1>Player Value v1</h1>
        <p class="lede">
          Explainable alias-based summaries from local decision events, tracking, and recognition quality signals.
        </p>
      </div>
      <RouterLink class="button-link" data-testid="player-value-trends-link" to="/player-value/trends">View trends</RouterLink>
      <button class="primary" :disabled="isBuilding" @click="buildPlayerValue">
        {{ isBuilding ? 'Building…' : 'Build Player Value' }}
      </button>
    </header>


    <TrustCaveatGate
      surface="player-value"
      title="Trust caveat"
      message="Court IQ outputs are decision-support signals based on local sample data, aliases, decision events, rules, and available evidence. Player Value is not an official scouting grade. Review confidence, warnings, and evidence before using recommendations."
    />

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="muted">Loading Player Value summaries…</p>

    <div v-if="playerValue?.warnings.length" class="warning-card">
      <strong>Build warnings</strong>
      <ul>
        <li v-for="warning in playerValue.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </div>

    <p v-if="playerValue" class="muted">Generated {{ formatDate(playerValue.generated_at) }}</p>

    <div v-if="playerValue?.summaries.length" class="table-card">
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Project</th>
            <th>Player key</th>
            <th>Display name</th>
            <th>Team side</th>
            <th>Player Value</th>
            <th>Confidence</th>
            <th>Events</th>
            <th>Warnings</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="summary in playerValue.summaries" :key="rowKey(summary)">
            <tr>
              <td><button class="ghost" @click="toggle(summary)">{{ expandedKeys.has(rowKey(summary)) ? 'Hide' : 'Expand' }}</button></td>
              <td>{{ summary.project_id }}</td>
              <td><code>{{ summary.player_key }}</code></td>
              <td>{{ summary.display_name ?? '—' }}</td>
              <td>{{ summary.team_side }}</td>
              <td>{{ formatNumber(summary.player_value_score) }}</td>
              <td>{{ formatPercent(summary.confidence) }}</td>
              <td>{{ summary.decision_event_count }}</td>
              <td class="warning-cell">{{ describeWarnings(summary) }}</td>
              <td>
                <RouterLink class="button-link" data-testid="player-value-evidence-link" :to="{ name: 'player-value-detail', params: { projectId: summary.project_id, playerKey: summary.player_key } }">
                  View Evidence
                </RouterLink>
              </td>
            </tr>
            <tr v-if="expandedKeys.has(rowKey(summary))" class="expanded-row">
              <td colspan="10">
                <div class="expanded-grid">
                  <section>
                    <h2>Component breakdown</h2>
                    <table class="nested-table">
                      <thead>
                        <tr>
                          <th>Component</th>
                          <th>Value</th>
                          <th>Weight</th>
                          <th>Contribution</th>
                          <th>Explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="component in summary.components" :key="component.name">
                          <td>{{ component.name }}</td>
                          <td>{{ formatNumber(component.value) }}</td>
                          <td>{{ formatPercent(component.weight) }}</td>
                          <td>{{ formatNumber(component.contribution) }}</td>
                          <td>{{ component.explanation }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </section>
                  <section>
                    <h2>Trace summary</h2>
                    <dl class="trace-list">
                      <dt>Projects</dt><dd>{{ summary.trace.project_ids.join(', ') || '—' }}</dd>
                      <dt>Tracks</dt><dd>{{ summary.trace.track_ids.join(', ') || '—' }}</dd>
                      <dt>Prompts</dt><dd>{{ summary.trace.prompt_ids.join(', ') || '—' }}</dd>
                      <dt>Decision events</dt><dd>{{ summary.trace.decision_event_ids.join(', ') || '—' }}</dd>
                      <dt>Sources</dt><dd>{{ summary.trace.source_ids.join(', ') || '—' }}</dd>
                    </dl>
                  </section>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div v-else-if="playerValue && !playerValue.summaries.length" class="empty-card">
      No Player Value summaries were generated. Build decision events first, then ensure prompt/option traces or aliases can link local track IDs.
    </div>
  </section>
</template>
