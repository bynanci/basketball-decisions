<script setup lang="ts">
import TrustCaveatGate from '../components/TrustCaveatGate.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient, type PracticePlan, type PracticePlanDuration, type PracticePlanListItem } from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'

const router = useRouter()
const plans = ref<PracticePlanListItem[]>([])
const selectedPlan = ref<PracticePlan | null>(null)
const title = ref('Practice Plan')
const duration = ref<PracticePlanDuration>(90)
const projectId = ref('')
const playerKey = ref('')
const playerKeys = ref('')
const maxDrillBlocks = ref(5)
const createdBy = ref('')
const notes = ref('')
const isLoading = ref(false)
const isBuilding = ref(false)
const isStartingExecution = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')

const durationOptions: PracticePlanDuration[] = [60, 75, 90, 120]
const blocks = computed(() => selectedPlan.value?.blocks ?? [])

function formatList(items: string[]) {
  return items.length ? items.join(', ') : 'Any'
}

function parsePlayerKeys() {
  return playerKeys.value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

async function loadPlans() {
  const response = await apiClient.listPracticePlans()
  plans.value = response.plans
}

async function selectPlan(planId: string) {
  selectedPlan.value = await apiClient.getPracticePlan(planId)
}

async function refresh() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    await loadPlans()
    if (!selectedPlan.value && plans.value.length) {
      await selectPlan(plans.value[0].plan_id)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load practice plans.'
  } finally {
    isLoading.value = false
  }
}

async function startExecution() {
  if (!selectedPlan.value) return
  isStartingExecution.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    const execution = await apiClient.createPracticeExecution({
      plan_id: selectedPlan.value.plan_id,
      started_by: createdBy.value.trim() || null,
      notes: 'Started from Practice Plans page.'
    })
    statusMessage.value = `Started execution ${execution.execution_id}.`
    router.push(`/practice-executions/${execution.execution_id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to start practice execution.'
  } finally {
    isStartingExecution.value = false
  }
}

async function buildPlan() {
  isBuilding.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    selectedPlan.value = await apiClient.buildPracticePlan({
      title: title.value.trim() || 'Practice Plan',
      total_duration_minutes: duration.value,
      project_id: projectId.value.trim() || null,
      player_key: playerKey.value.trim() || null,
      player_keys: parsePlayerKeys(),
      max_drill_blocks: maxDrillBlocks.value,
      created_by: createdBy.value.trim() || null,
      notes: notes.value.trim() || null
    })
    statusMessage.value = `Saved ${selectedPlan.value.total_duration_minutes}-minute plan with ${selectedPlan.value.blocks.length} blocks.`
    await loadPlans()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to build practice plan.'
  } finally {
    isBuilding.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="page practice-plans-page" data-testid="practice-plans-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">M23 Practice Plan Builder</p>
        <h1>Practice Plans</h1>
        <p class="lede">Build time-boxed 60, 75, 90, or 120 minute plans from deterministic drill recommendations and export Markdown or JSON for coach review before use.</p>
      </div>
      <div class="button-row">
        <button class="ghost" :disabled="isLoading" @click="refresh">{{ isLoading ? 'Refreshing…' : 'Refresh' }}</button>
        <button class="primary" :disabled="isBuilding" @click="buildPlan">{{ isBuilding ? 'Building…' : 'Build plan' }}</button>
      </div>
    </header>


    <TrustCaveatGate
      surface="practice-plans"
      title="Trust caveat"
      message="Court IQ outputs are decision-support signals based on local sample data, aliases, decision events, rules, and available evidence. Player Value is not an official scouting grade. Review confidence, warnings, and evidence before using recommendations."
      compact
    />

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p class="muted">Recommendations are generated from available local evidence and should be reviewed by a coach or analyst before use.</p>
    <ErrorState v-if="errorMessage" title="Practice plan API error" :message="errorMessage" action-label="Open Drill Recommendations" action-to="/drills" />

    <section class="card practice-builder">
      <h2>Builder</h2>
      <div class="form-grid three-column">
        <label>
          Title
          <input v-model="title" type="text" />
        </label>
        <label>
          Total duration
          <select v-model.number="duration">
            <option v-for="option in durationOptions" :key="option" :value="option">{{ option }} minutes</option>
          </select>
        </label>
        <label>
          Max drill blocks
          <input v-model.number="maxDrillBlocks" type="number" min="1" max="10" />
        </label>
        <label>
          Project filter
          <input v-model="projectId" type="text" placeholder="Optional project_id" />
        </label>
        <label>
          Primary player key
          <input v-model="playerKey" type="text" placeholder="Optional player_key" />
        </label>
        <label>
          Additional player keys
          <input v-model="playerKeys" type="text" placeholder="Comma-separated" />
        </label>
        <label>
          Created by
          <input v-model="createdBy" type="text" placeholder="Optional" />
        </label>
        <label class="wide-field">
          Notes
          <input v-model="notes" type="text" placeholder="Optional builder note" />
        </label>
      </div>
      <p class="muted">Plans use local recommendation evidence and catalog-authored drill cues only. Calendar integration, PDF/DOCX export, medical or injury advice, and season planning are intentionally excluded.</p>
    </section>

    <section v-if="selectedPlan" class="card">
      <div class="section-header">
        <div>
          <p class="eyebrow">Selected plan</p>
          <h2>{{ selectedPlan.title }}</h2>
          <p class="muted">{{ selectedPlan.total_duration_minutes }} minutes · {{ blocks.length }} blocks · {{ selectedPlan.plan_id }}</p>
        </div>
        <div class="button-row">
          <a class="button secondary-button" :href="apiClient.practicePlanMarkdownUrl(selectedPlan.plan_id)" target="_blank" rel="noreferrer">Markdown</a>
          <a class="button secondary-button" :href="apiClient.practicePlanJsonUrl(selectedPlan.plan_id)" target="_blank" rel="noreferrer">JSON</a>
          <button class="primary" :disabled="isStartingExecution" @click="startExecution">{{ isStartingExecution ? 'Starting…' : 'Start Execution' }}</button>
        </div>
      </div>
      <p v-if="selectedPlan.notes" class="note-box"><strong>Notes:</strong> {{ selectedPlan.notes }}</p>
      <dl class="meta-grid">
        <div><dt>Roles</dt><dd>{{ formatList(selectedPlan.target_roles) }}</dd></div>
        <div><dt>Situations</dt><dd>{{ formatList(selectedPlan.target_situations) }}</dd></div>
        <div><dt>Player keys</dt><dd>{{ formatList(selectedPlan.player_keys) }}</dd></div>
        <div><dt>Evidence refs</dt><dd>{{ selectedPlan.evidence_refs.length }}</dd></div>
      </dl>
      <ul v-if="selectedPlan.warnings.length" class="evidence-list">
        <li v-for="warning in selectedPlan.warnings" :key="warning"><strong>Warning</strong><small>{{ warning }}</small></li>
      </ul>
    </section>

    <EmptyState
      v-if="selectedPlan && !blocks.length"
      title="No recommendations in this plan"
      message="No drill blocks were available for this scope yet."
      action-label="Open Drill Recommendations"
      action-to="/drills"
    />
    <section class="recommendation-grid">
      <article v-for="block in blocks" :key="block.block_id" class="card recommendation-card">
        <div class="section-header">
          <div>
            <span class="priority">{{ block.block_type }}</span>
            <h2>{{ block.start_minute }}–{{ block.end_minute }} min · {{ block.title }}</h2>
          </div>
          <strong>{{ block.duration_minutes }} min</strong>
        </div>
        <dl class="meta-grid">
          <div><dt>Roles</dt><dd>{{ formatList(block.target_roles) }}</dd></div>
          <div><dt>Situations</dt><dd>{{ formatList(block.target_situations) }}</dd></div>
          <div><dt>Player keys</dt><dd>{{ formatList(block.player_keys) }}</dd></div>
          <div><dt>Evidence</dt><dd>{{ block.evidence_refs.length }} refs</dd></div>
        </dl>
        <div class="list-columns">
          <div>
            <h3>Coaching cues</h3>
            <ul><li v-for="cue in block.coaching_cues" :key="cue">{{ cue }}</li><li v-if="!block.coaching_cues.length" class="muted">No generated cues for this fixed block.</li></ul>
          </div>
          <div>
            <h3>Success metrics</h3>
            <ul><li v-for="metric in block.success_metrics" :key="metric">{{ metric }}</li></ul>
          </div>
        </div>
        <div v-if="block.warnings.length">
          <h3>Warnings</h3>
          <ul class="evidence-list">
            <li v-for="warning in block.warnings" :key="`${block.block_id}-${warning}`"><strong>Warning</strong><small>{{ warning }}</small></li>
          </ul>
        </div>
        <h3>Evidence refs</h3>
        <ul class="evidence-list">
          <li v-for="ref in block.evidence_refs" :key="`${block.block_id}-${ref.source}-${ref.ref_id}-${ref.detail}`">
            <strong>{{ ref.source }}</strong>
            <span>{{ ref.ref_id || ref.prompt_id || ref.player_key || 'artifact' }}</span>
            <small>{{ ref.detail }}</small>
          </li>
          <li v-if="!block.evidence_refs.length" class="muted">No evidence refs attached to this fixed operational block.</li>
        </ul>
      </article>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Saved plans</h2>
        <span class="muted">{{ plans.length }} plans</span>
      </div>
      <div class="catalog-list">
        <button v-for="plan in plans" :key="plan.plan_id" class="catalog-item link-button" @click="selectPlan(plan.plan_id)">
          <strong>{{ plan.title }}</strong>
          <span>{{ plan.total_duration_minutes }} minutes · {{ plan.plan_id }}</span>
          <small>{{ formatList(plan.target_roles) }} · {{ formatList(plan.target_situations) }}</small>
        </button>
      </div>
    </section>
  </section>
</template>
