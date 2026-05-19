<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient, type WorkflowListItem, type WorkflowTemplateKey } from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'

const router = useRouter()
const workflows = ref<WorkflowListItem[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const selectedTemplate = ref<WorkflowTemplateKey>('BUILD_PLAYER_VALUE')
const projectId = ref('')

const templateOptions: Array<{ key: WorkflowTemplateKey; label: string; detail: string }> = [
  { key: 'BUILD_PLAYER_VALUE', label: 'Build Player Value', detail: 'Tracking review → aliases → decision events → Player Value' },
  { key: 'IMPROVE_DATA_QUALITY', label: 'Improve Data Quality', detail: 'Review queue → dataset health → model readiness' },
  { key: 'TRAINING_RECOMMENDATION', label: 'Training Recommendation Support', detail: 'Player Value → drills → practice plan → execution' },
  { key: 'COACH_REPORT', label: 'Coach Report', detail: 'Readiness checks → deterministic report export' },
  { key: 'MODEL_GOVERNANCE', label: 'Model Governance', detail: 'Dataset health → review queue → active model' }
]

async function loadWorkflows() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.listWorkflows()
    workflows.value = response.workflows
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load workflows.'
  } finally {
    isLoading.value = false
  }
}

async function startWorkflow() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const workflow = await apiClient.createWorkflow({ template_key: selectedTemplate.value, project_id: projectId.value || null })
    await router.push(`/workflows/${workflow.workflow_id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to start workflow.'
  } finally {
    isLoading.value = false
  }
}

function statusClass(status: string) {
  return `status-${status.toLowerCase().replace(/_/g, '-')}`
}

onMounted(loadWorkflows)
</script>

<template>
  <section class="page-stack" data-testid="workflows-page">
    <div class="hero-card">
      <p class="eyebrow">M27 Guided Workflow Orchestrator</p>
      <h1>Guided Workflows</h1>
      <p>Start local, explicit workflow checklists. Steps point to existing tools and never execute underlying operations automatically.</p>
    </div>

    <ErrorState v-if="errorMessage" title="Workflow API error" :message="errorMessage" action-label="Open Development Dashboard" action-to="/development-dashboard" />

    <section class="card">
      <div class="section-header">
        <div>
          <h2>Start a workflow</h2>
          <p class="muted">Choose a template. Optional project ID scopes prerequisite checks.</p>
        </div>
        <button :disabled="isLoading" @click="startWorkflow">Review guided workflow steps</button>
      </div>
      <div class="form-grid">
        <label>
          Workflow template
          <select v-model="selectedTemplate">
            <option v-for="option in templateOptions" :key="option.key" :value="option.key">{{ option.label }} — {{ option.detail }}</option>
          </select>
        </label>
        <label>
          Project ID (optional)
          <input v-model="projectId" placeholder="project-123" />
        </label>
      </div>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Saved workflows</h2>
        <button class="secondary" :disabled="isLoading" @click="loadWorkflows">Refresh list</button>
      </div>
      <p v-if="isLoading" class="status">Loading workflows…</p>
      <EmptyState v-else-if="!workflows.length" title="No guided workflows yet" message="Start a template to track prerequisites and blocked steps." action-label="Open sample data intake" action-to="/" />
      <div v-else class="table-card compact-table">
        <table>
          <thead>
            <tr><th>Workflow</th><th>Status</th><th>Progress</th><th>Scope</th><th>Updated</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="workflow in workflows" :key="workflow.workflow_id">
              <td><strong>{{ workflow.title }}</strong><br /><code>{{ workflow.workflow_id }}</code></td>
              <td><span class="pill" :class="statusClass(workflow.status)">{{ workflow.status }}</span></td>
              <td>{{ workflow.completed_step_count }} / {{ workflow.total_step_count }} complete<span v-if="workflow.blocked_step_count"> · {{ workflow.blocked_step_count }} blocked</span></td>
              <td>{{ workflow.project_id ?? 'All projects' }}</td>
              <td>{{ new Date(workflow.updated_at).toLocaleString() }}</td>
              <td><RouterLink class="button-link" :to="`/workflows/${workflow.workflow_id}`">{{ workflow.blocked_step_count ? 'Resolve blocked steps' : 'Open' }}</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
