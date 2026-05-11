<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, isApiClientError, type DecisionRuleDraft, type DecisionRuleSet } from '../api/client'

const drafts = ref<DecisionRuleDraft[]>([])
const ruleSets = ref<DecisionRuleSet[]>([])
const activeRuleSet = ref<DecisionRuleSet | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const errorCode = ref('')
const reviewerName = ref('Coach')
const newRuleSetName = ref('')
const selectedRuleSetId = ref('')

const pendingDrafts = computed(() => drafts.value.filter((draft) => draft.status === 'DRAFT'))
const reviewedDrafts = computed(() => drafts.value.filter((draft) => draft.status !== 'DRAFT'))

function showError(error: unknown, fallback: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
  } else {
    errorCode.value = 'FRONTEND_ERROR'
    errorMessage.value = error instanceof Error ? error.message : fallback
  }
}

async function loadDecisionRules() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [draftResponse, ruleSetResponse] = await Promise.all([apiClient.listDecisionRuleDrafts(), apiClient.listDecisionRuleSets()])
    drafts.value = draftResponse
    ruleSets.value = ruleSetResponse.rule_sets
    activeRuleSet.value = ruleSetResponse.active_rule_set ?? null
    if (!selectedRuleSetId.value && activeRuleSet.value) selectedRuleSetId.value = activeRuleSet.value.rule_set_id
  } catch (error) {
    showError(error, 'Could not load decision rules.')
  } finally {
    isLoading.value = false
  }
}

async function approveDraft(draft: DecisionRuleDraft) {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.approveDecisionRuleDraft(draft.draft_id, {
      rule_set_id: selectedRuleSetId.value || null,
      approved_by: reviewerName.value || null
    })
    statusMessage.value = 'Rule draft approved into the selected rule set.'
    await loadDecisionRules()
  } catch (error) {
    showError(error, 'Could not approve the rule draft.')
  } finally {
    isSaving.value = false
  }
}

async function rejectDraft(draft: DecisionRuleDraft) {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.rejectDecisionRuleDraft(draft.draft_id)
    statusMessage.value = 'Rule draft rejected. No active rule was created.'
    await loadDecisionRules()
  } catch (error) {
    showError(error, 'Could not reject the rule draft.')
  } finally {
    isSaving.value = false
  }
}

async function createRuleSet() {
  if (!newRuleSetName.value.trim()) return
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const ruleSet = await apiClient.createDecisionRuleSet({ name: newRuleSetName.value.trim() })
    selectedRuleSetId.value = ruleSet.rule_set_id
    newRuleSetName.value = ''
    statusMessage.value = 'Rule set created.'
    await loadDecisionRules()
  } catch (error) {
    showError(error, 'Could not create the rule set.')
  } finally {
    isSaving.value = false
  }
}

async function activateRuleSet(ruleSet: DecisionRuleSet) {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.activateDecisionRuleSet(ruleSet.rule_set_id)
    selectedRuleSetId.value = ruleSet.rule_set_id
    statusMessage.value = 'Rule set activated.'
    await loadDecisionRules()
  } catch (error) {
    showError(error, 'Could not activate the rule set.')
  } finally {
    isSaving.value = false
  }
}

async function disableRule(ruleId: string) {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.updateDecisionRule(ruleId, { status: 'DISABLED' })
    statusMessage.value = 'Rule disabled.'
    await loadDecisionRules()
  } catch (error) {
    showError(error, 'Could not disable the rule.')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadDecisionRules)
</script>

<template>
  <section class="card decision-rules-hero">
    <p class="eyebrow">M15 Decision Rule Approval Workflow</p>
    <h1>Approve reference-derived rule drafts before they become active rules</h1>
    <p>
      Reference video breakdowns create pending rule drafts only. A human reviewer must approve a draft into a local JSON rule set before
      Decision Engine v2 can consume it later; this workflow does not train a model or auto-promote reference-only data.
    </p>
    <p v-if="statusMessage" class="success-message">{{ statusMessage }}</p>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
    </div>
  </section>

  <section class="card controls-grid">
    <div>
      <p class="eyebrow">Reviewer</p>
      <label>Approved by<input v-model="reviewerName" placeholder="Coach" /></label>
    </div>
    <div>
      <p class="eyebrow">Target rule set</p>
      <label>
        Approve into
        <select v-model="selectedRuleSetId">
          <option value="">Active/default rule set</option>
          <option v-for="ruleSet in ruleSets" :key="ruleSet.rule_set_id" :value="ruleSet.rule_set_id">
            {{ ruleSet.name }} v{{ ruleSet.version }}{{ ruleSet.active ? ' (active)' : '' }}
          </option>
        </select>
      </label>
    </div>
    <form @submit.prevent="createRuleSet">
      <p class="eyebrow">Create rule set</p>
      <label>Name<input v-model="newRuleSetName" placeholder="Playoff reads" /></label>
      <button type="submit" :disabled="isSaving || !newRuleSetName.trim()">Create Rule Set</button>
    </form>
  </section>

  <section class="card">
    <div class="table-header"><h2>Pending rule drafts</h2><span>{{ pendingDrafts.length }} pending</span></div>
    <p v-if="isLoading">Loading decision rules…</p>
    <div v-else class="draft-list">
      <article v-for="draft in pendingDrafts" :key="draft.draft_id" class="draft-card">
        <div>
          <strong>{{ draft.court_role }} · {{ draft.situation_type }}</strong>
          <p><strong>Condition:</strong> {{ draft.condition_text }}</p>
          <p><strong>Positive cue:</strong> {{ draft.positive_cue }}</p>
          <p><strong>Negative cue:</strong> {{ draft.negative_cue }}</p>
          <p><strong>Suggested weight:</strong> {{ draft.suggested_weight }}</p>
          <p class="muted">Reference-only origin stays metadata; approving creates a rule, not training data.</p>
        </div>
        <div class="action-buttons">
          <button type="button" :disabled="isSaving" @click="approveDraft(draft)">Approve</button>
          <button type="button" class="secondary-button" :disabled="isSaving" @click="rejectDraft(draft)">Reject</button>
        </div>
      </article>
      <p v-if="pendingDrafts.length === 0">No pending rule drafts.</p>
    </div>
  </section>

  <section class="card">
    <div class="table-header">
      <div>
        <p class="eyebrow">Active rule set</p>
        <h2>{{ activeRuleSet?.name ?? 'No active rule set' }}</h2>
      </div>
      <span v-if="activeRuleSet">v{{ activeRuleSet.version }} · {{ activeRuleSet.rules.length }} rules</span>
    </div>
    <div class="table-scroll">
      <table>
        <thead><tr><th>Status</th><th>Role</th><th>Situation</th><th>Condition</th><th>Positive cue</th><th>Negative cue</th><th>Weight</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="rule in activeRuleSet?.rules ?? []" :key="rule.rule_id">
            <td><span :class="rule.status === 'ACTIVE' ? 'active-badge' : 'disabled-badge'">{{ rule.status }}</span></td>
            <td>{{ rule.court_role }}</td>
            <td>{{ rule.situation_type }}</td>
            <td>{{ rule.condition_text }}</td>
            <td>{{ rule.positive_cue }}</td>
            <td>{{ rule.negative_cue }}</td>
            <td>{{ rule.weight }}</td>
            <td><button type="button" class="secondary-button" :disabled="isSaving || rule.status === 'DISABLED'" @click="disableRule(rule.rule_id)">Disable rule</button></td>
          </tr>
          <tr v-if="!activeRuleSet || activeRuleSet.rules.length === 0"><td colspan="8">No approved rules in the active rule set.</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <div class="table-header"><h2>Rule sets</h2><span>{{ ruleSets.length }} total</span></div>
    <div class="rule-set-list">
      <article v-for="ruleSet in ruleSets" :key="ruleSet.rule_set_id" class="rule-set-card">
        <div>
          <h3>{{ ruleSet.name }} v{{ ruleSet.version }}</h3>
          <p>{{ ruleSet.rules.length }} rules · {{ ruleSet.active ? 'Active' : 'Inactive' }}</p>
        </div>
        <button type="button" :disabled="isSaving || ruleSet.active" @click="activateRuleSet(ruleSet)">Activate rule set</button>
      </article>
      <p v-if="ruleSets.length === 0">No rule sets yet. Approving a draft can create the default active rule set.</p>
    </div>
  </section>

  <section class="card" v-if="reviewedDrafts.length">
    <div class="table-header"><h2>Reviewed drafts</h2><span>{{ reviewedDrafts.length }} reviewed</span></div>
    <ul>
      <li v-for="draft in reviewedDrafts" :key="draft.draft_id">{{ draft.status }} · {{ draft.court_role }} · {{ draft.condition_text }}</li>
    </ul>
  </section>
</template>

<style scoped>
.decision-rules-hero,
.draft-list,
.rule-set-list {
  display: grid;
  gap: 1rem;
}

.controls-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.controls-grid label,
.controls-grid form {
  display: grid;
  gap: 0.35rem;
  font-weight: 700;
}

.controls-grid select,
.controls-grid input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  display: block;
  margin: 0.5rem 0 1rem;
  padding: 0.75rem;
  width: min(100%, 520px);
}

.draft-card,
.rule-set-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  padding: 1rem;
}

.table-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.table-scroll {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  min-width: 1100px;
  width: 100%;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.7rem;
  text-align: left;
  vertical-align: top;
}

.active-badge,
.disabled-badge {
  border-radius: 999px;
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.2rem 0.55rem;
}

.active-badge {
  background: #dcfce7;
  color: #166534;
}

.disabled-badge {
  background: #e2e8f0;
  color: #475569;
}

.success-message {
  color: #166534;
  font-weight: 800;
}
</style>
