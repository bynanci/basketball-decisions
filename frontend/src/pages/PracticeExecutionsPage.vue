<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, type PracticeExecutionListItem, type PracticeFeedbackSignal } from '../api/client'

const executions = ref<PracticeExecutionListItem[]>([])
const signals = ref<PracticeFeedbackSignal[]>([])
const isLoading = ref(false)
const errorMessage = ref('')

function percent(value: number) {
  return `${Math.round(value * 100)}%`
}

async function refresh() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [executionResponse, signalResponse] = await Promise.all([apiClient.listPracticeExecutions(), apiClient.listPracticeFeedbackSignals()])
    executions.value = executionResponse.executions
    signals.value = signalResponse.signals
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to load practice executions.'
  } finally {
    isLoading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="page practice-executions-page" data-testid="practice-executions-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">M24 Practice Execution & Feedback Loop</p>
        <h1>Practice Executions</h1>
        <p class="lede">Track execution sessions created from saved practice plans, capture coach/player notes, and review deterministic feedback signals.</p>
      </div>
      <div class="button-row">
        <RouterLink class="button secondary-button" to="/practice-plans">Practice Plans</RouterLink>
        <button class="ghost" :disabled="isLoading" @click="refresh">{{ isLoading ? 'Refreshing…' : 'Refresh' }}</button>
      </div>
    </header>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

    <section class="card">
      <div class="section-header">
        <h2>Saved executions</h2>
        <span class="muted">{{ executions.length }} sessions</span>
      </div>
      <div class="catalog-list">
        <RouterLink v-for="execution in executions" :key="execution.execution_id" class="catalog-item" :to="`/practice-executions/${execution.execution_id}`">
          <strong>{{ execution.plan_title }}</strong>
          <span>{{ percent(execution.completion_rate) }} complete · {{ execution.planned_duration_minutes }} minutes · {{ execution.execution_id }}</span>
          <small>{{ execution.skipped_count }} skipped · {{ execution.modified_count }} modified · plan {{ execution.plan_id }}</small>
        </RouterLink>
        <p v-if="!executions.length" class="muted">No execution sessions yet. Start one from Practice Plans.</p>
      </div>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Feedback signals</h2>
        <span class="muted">{{ signals.length }} signals</span>
      </div>
      <ul class="evidence-list">
        <li v-for="signal in signals" :key="`${signal.execution_id}-${signal.signal_type}-${signal.block_id}-${signal.reason}`">
          <strong>{{ signal.signal_type }}</strong>
          <span>{{ signal.severity }} · {{ signal.execution_id }}</span>
          <small>{{ signal.reason }}</small>
        </li>
        <li v-if="!signals.length" class="muted">Signals appear after execution blocks are updated with statuses, ratings, notes, durations, and metric results.</li>
      </ul>
    </section>
  </section>
</template>
