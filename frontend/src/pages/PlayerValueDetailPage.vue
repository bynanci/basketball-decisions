<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ConfidenceHelp from '../components/ConfidenceHelp.vue'
import { apiClient, type PlayerValueEvidenceResponse } from '../api/client'

const props = defineProps<{
  projectId: string
  playerKey: string
}>()

const evidence = ref<PlayerValueEvidenceResponse | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')

const summary = computed(() => evidence.value?.summary ?? null)
const hasEvents = computed(() => Boolean(evidence.value?.events.length))

function formatNumber(value?: number | null, maximumFractionDigits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(value)
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${formatNumber(value * 100)}%`
}

function formatList(values?: string[] | null) {
  return values?.length ? values.join(', ') : '—'
}

function optionPair(selected?: string | null, correct?: string | null) {
  return `${selected || '—'} / ${correct || '—'}`
}

function matchedRuleLabels(event: PlayerValueEvidenceResponse['events'][number]) {
  return event.rule_application.results
    .filter((result) => result.matched)
    .map((result) => `${result.rule_id} (${formatNumber(result.score_delta)})`)
}

async function loadEvidence() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    evidence.value = await apiClient.getPlayerValueEvidence(props.projectId, props.playerKey)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load Player Value evidence.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadEvidence)
</script>

<template>
  <section class="page player-value-detail-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Player Value Evidence</p>
        <h1><code>{{ props.playerKey }}</code></h1>
        <p class="lede">
          Inspect local decision events, prompt context, source tracks, frame context tracks, and confidence warnings.
        </p>
        <p class="muted">
          source_track_ids are identity-bearing. context_track_ids are frame context only.
        </p>
      </div>
      <RouterLink class="button-link" to="/player-value">Back to Player Value</RouterLink>
    </header>

    <p v-if="isLoading" class="muted">Loading evidence…</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

    <template v-if="summary && evidence">
      <section class="summary-grid">
        <article class="stat-card">
          <span>Project</span>
          <strong>{{ summary.project_id }}</strong>
        </article>
        <article class="stat-card">
          <span>Display name</span>
          <strong>{{ summary.display_name ?? '—' }}</strong>
        </article>
        <article class="stat-card">
          <span>Team side</span>
          <strong>{{ summary.team_side || 'UNKNOWN' }}</strong>
        </article>
        <article class="stat-card">
          <span>Role hint</span>
          <strong>{{ summary.role_hint ?? '—' }}</strong>
        </article>
        <article class="stat-card">
          <span>Player Value</span>
          <strong>{{ formatNumber(summary.player_value_score) }}</strong>
        </article>
        <article class="stat-card">
          <span>Confidence</span>
          <strong>{{ formatPercent(summary.confidence) }}</strong>
        </article>
        <ConfidenceHelp variant="analyst" compact />
      </section>

      <section v-if="summary.warnings.length" class="warning-card">
        <h2>Summary warnings</h2>
        <ul>
          <li v-for="warning in summary.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </section>

      <section class="table-card">
        <h2>Component Breakdown</h2>
        <table>
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

      <section class="table-card">
        <h2>Role Breakdown</h2>
        <table>
          <thead>
            <tr>
              <th>Court role</th>
              <th>Events</th>
              <th>Avg score</th>
              <th>Avg opportunity cost</th>
              <th>Correct rate</th>
              <th>Timeout rate</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in evidence.role_breakdown" :key="item.court_role ?? 'unknown-role'">
              <td>{{ item.court_role ?? 'UNKNOWN' }}</td>
              <td>{{ item.event_count }}</td>
              <td>{{ formatNumber(item.avg_role_adjusted_score) }}</td>
              <td>{{ formatNumber(item.avg_opportunity_cost) }}</td>
              <td>{{ formatPercent(item.correct_rate) }}</td>
              <td>{{ formatPercent(item.timeout_rate) }}</td>
            </tr>
            <tr v-if="!evidence.role_breakdown.length"><td colspan="6">No role evidence yet.</td></tr>
          </tbody>
        </table>
      </section>

      <section class="table-card">
        <h2>Situation Breakdown</h2>
        <table>
          <thead>
            <tr>
              <th>Situation</th>
              <th>Events</th>
              <th>Avg score</th>
              <th>Avg opportunity cost</th>
              <th>Correct rate</th>
              <th>Timeout rate</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in evidence.situation_breakdown" :key="item.situation_type ?? 'unknown-situation'">
              <td>{{ item.situation_type ?? 'UNKNOWN' }}</td>
              <td>{{ item.event_count }}</td>
              <td>{{ formatNumber(item.avg_role_adjusted_score) }}</td>
              <td>{{ formatNumber(item.avg_opportunity_cost) }}</td>
              <td>{{ formatPercent(item.correct_rate) }}</td>
              <td>{{ formatPercent(item.timeout_rate) }}</td>
            </tr>
            <tr v-if="!evidence.situation_breakdown.length"><td colspan="6">No situation evidence yet.</td></tr>
          </tbody>
        </table>
      </section>

      <section class="table-card">
        <h2>Decision Event Evidence</h2>
        <p class="muted">UNKNOWN attribution is shown instead of hidden whenever identity evidence is missing or ambiguous.</p>
        <table>
          <thead>
            <tr>
              <th>Prompt</th>
              <th>Frame</th>
              <th>Role</th>
              <th>Situation</th>
              <th>Selected / Correct</th>
              <th>Base / Rule / Final</th>
              <th>Matched rules</th>
              <th>Opp. cost</th>
              <th>source_track_ids</th>
              <th>context_track_ids</th>
              <th>Warnings</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in evidence.events" :key="event.decision_event_id">
              <td>
                <code>{{ event.prompt_id }}</code>
                <div class="muted">{{ event.prompt_question ?? 'Prompt missing' }}</div>
                <div class="muted">{{ event.selected_option_label ?? '—' }} / {{ event.correct_option_label ?? '—' }}</div>
              </td>
              <td>{{ formatNumber(event.frame_index, 0) }}</td>
              <td>{{ event.court_role_target ?? 'UNKNOWN' }}</td>
              <td>{{ event.situation_type ?? 'UNKNOWN' }}</td>
              <td>{{ optionPair(event.selected_option_id, event.correct_option_id) }}</td>
              <td>
                {{ formatNumber(event.base_score ?? event.raw_score) }} / {{ formatNumber(event.rule_score_delta) }} / {{ formatNumber(event.final_score ?? event.role_adjusted_score) }}
                <div v-if="event.score_capped" class="muted">Clipped to 0..100</div>
              </td>
              <td>
                <span v-if="matchedRuleLabels(event).length">{{ formatList(matchedRuleLabels(event)) }}</span>
                <span v-else class="muted">No matched rules</span>
                <div class="muted">{{ event.rule_application.matched_rule_count }} hits · {{ event.rule_application.missed_rule_count }} misses</div>
              </td>
              <td>{{ formatNumber(event.opportunity_cost) }}</td>
              <td><code>{{ formatList(event.source_track_ids) }}</code></td>
              <td><code>{{ formatList(event.context_track_ids) }}</code></td>
              <td class="warning-cell">{{ formatList(event.evidence_warnings) }}</td>
              <td>
                <RouterLink :to="{ name: 'project', params: { projectId: event.project_id } }">Project</RouterLink>
                <br />
                <RouterLink :to="{ name: 'quiz-play', params: { projectId: event.project_id, promptId: event.prompt_id } }">Prompt</RouterLink>
              </td>
            </tr>
            <tr v-if="!hasEvents"><td colspan="12">No decision event evidence was found for this summary.</td></tr>
          </tbody>
        </table>
      </section>

      <section class="warning-card">
        <h2>Evidence Warning Panel</h2>
        <p class="muted">
          This panel surfaces missing prompts, missing events, UNKNOWN attribution, absent source_track_ids,
          ambiguous identity fallback, and low confidence. Player Value is local explainable aggregation, not a scouting-grade model.
        </p>
        <ul v-if="evidence.warning_summary.length">
          <li v-for="warning in evidence.warning_summary" :key="warning">{{ warning }}</li>
        </ul>
        <p v-else class="muted">No evidence warnings were reported.</p>
      </section>
    </template>
  </section>
</template>
