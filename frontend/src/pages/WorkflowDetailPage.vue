<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, type Workflow } from '../api/client'

const props = defineProps<{ workflowId: string }>()
const workflow = ref<Workflow | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')
const note = ref('')

const satisfiedCount = computed(() => workflow.value?.prerequisites.filter((item) => item.satisfied).length ?? 0)

async function loadWorkflow() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    workflow.value = await apiClient.getWorkflow(props.workflowId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load workflow.'
  } finally {
    isLoading.value = false
  }
}

async function refreshWorkflow() {
  if (!workflow.value) return
  isLoading.value = true
  try {
    workflow.value = await apiClient.refreshWorkflow(workflow.value.workflow_id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to refresh workflow.'
  } finally {
    isLoading.value = false
  }
}

async function updateStep(stepId: string, status: 'COMPLETED' | 'SKIPPED') {
  if (!workflow.value) return
  isLoading.value = true
  try {
    workflow.value = await apiClient.updateWorkflowStep(workflow.value.workflow_id, stepId, { status, note: note.value || null })
    note.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to update workflow step.'
  } finally {
    isLoading.value = false
  }
}

function statusClass(status: string) {
  return `status-${status.toLowerCase().replace(/_/g, '-')}`
}

onMounted(loadWorkflow)
</script>

<template>
  <section class="page-stack">
    <div v-if="errorMessage" class="error-card">{{ errorMessage }}</div>
    <p v-if="isLoading && !workflow" class="status">Loading workflow…</p>

    <template v-if="workflow">
      <div class="hero-card">
        <p class="eyebrow">{{ workflow.template_key }}</p>
        <h1>{{ workflow.title }}</h1>
        <p>{{ workflow.description }}</p>
        <p><span class="pill" :class="statusClass(workflow.status)">{{ workflow.status }}</span> · {{ satisfiedCount }} / {{ workflow.prerequisites.length }} prerequisites satisfied</p>
        <div class="button-row">
          <button :disabled="isLoading" @click="refreshWorkflow">Refresh prerequisite checks</button>
          <RouterLink class="button-link" to="/workflows">Back to workflows</RouterLink>
        </div>
      </div>

      <div v-if="workflow.warnings.length" class="warning-card">
        <ul><li v-for="warning in workflow.warnings" :key="warning">{{ warning }}</li></ul>
      </div>

      <section class="card">
        <h2>Steps</h2>
        <label>
          Optional update note
          <input v-model="note" placeholder="Manual note for completed/skipped updates" />
        </label>
        <ol class="timeline-list">
          <li v-for="step in workflow.steps" :key="step.step_id" class="timeline-item">
            <div class="section-header">
              <div>
                <h3>{{ step.title }} <span class="pill" :class="statusClass(step.status)">{{ step.status }}</span></h3>
                <p>{{ step.description }}</p>
                <p class="muted">Completion check: {{ step.completion_prerequisite_key ?? 'manual' }}</p>
              </div>
              <div class="button-row">
                <RouterLink class="button-link" :to="step.href">{{ step.action_label }}</RouterLink>
                <button class="secondary" :disabled="isLoading" @click="updateStep(step.step_id, 'COMPLETED')">Mark complete</button>
                <button class="secondary" :disabled="isLoading" @click="updateStep(step.step_id, 'SKIPPED')">Skip</button>
              </div>
            </div>
            <ul v-if="step.notes.length" class="muted"><li v-for="item in step.notes" :key="item">{{ item }}</li></ul>
          </li>
        </ol>
      </section>

      <section class="card">
        <h2>Prerequisite checks</h2>
        <div class="table-card compact-table">
          <table>
            <thead><tr><th>Check</th><th>State</th><th>Detail</th><th>Artifact</th></tr></thead>
            <tbody>
              <tr v-for="item in workflow.prerequisites" :key="item.key">
                <td>{{ item.label }}<br /><code>{{ item.key }}</code></td>
                <td>{{ item.satisfied ? 'Satisfied' : 'Missing' }}</td>
                <td>{{ item.detail }}</td>
                <td><code>{{ item.artifact_path ?? 'project scoped' }}</code></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </section>
</template>
