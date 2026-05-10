<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { DecisionQuizOption, QuizAttemptResponse } from '../api/client'

const props = defineProps<{
  projectId: string
  result: QuizAttemptResponse
  selectedOption?: DecisionQuizOption | null
  correctOption?: DecisionQuizOption | null
}>()

const emit = defineEmits<{
  (event: 'retry'): void
}>()

const selectedOptionLabel = computed(() => formatOption(props.selectedOption, props.result.selected_option_id))
const correctOptionLabel = computed(() => formatOption(props.correctOption, props.result.correct_option_id))
const hasSelectedExpectedValue = computed(() => isFiniteNumber(props.result.selected_expected_value))
const hasCorrectExpectedValue = computed(() => isFiniteNumber(props.result.correct_expected_value))
const hasOpportunityCost = computed(() => isFiniteNumber(props.result.opportunity_cost))

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function formatNumber(value: number | null | undefined) {
  return isFiniteNumber(value) ? value.toFixed(2) : ''
}

function formatOption(option: DecisionQuizOption | null | undefined, fallbackOptionId: string) {
  if (!option) return fallbackOptionId
  const label = option.label.trim() || 'Decision'
  return `${option.option_id} — ${label}`
}
</script>

<template>
  <section class="quiz-result-panel" aria-live="polite">
    <header :class="['result-banner', result.is_correct ? 'correct' : 'incorrect']">
      <span class="result-kicker">Result</span>
      <strong>{{ result.is_correct ? 'Correct' : 'Not quite' }}</strong>
      <span>{{ result.is_correct ? 'You selected the best decision.' : 'Review the best available decision below.' }}</span>
    </header>

    <dl class="result-metrics">
      <div>
        <dt>Selected option</dt>
        <dd>{{ selectedOptionLabel }}</dd>
      </div>
      <div>
        <dt>Correct option</dt>
        <dd>{{ correctOptionLabel }}</dd>
      </div>
      <div>
        <dt>isCorrect</dt>
        <dd>{{ result.is_correct ? 'true' : 'false' }}</dd>
      </div>
      <div v-if="hasSelectedExpectedValue">
        <dt>Selected expected value</dt>
        <dd>{{ formatNumber(result.selected_expected_value) }}</dd>
      </div>
      <div v-if="hasCorrectExpectedValue">
        <dt>Correct expected value</dt>
        <dd>{{ formatNumber(result.correct_expected_value) }}</dd>
      </div>
      <div v-if="hasOpportunityCost">
        <dt>Opportunity cost</dt>
        <dd>{{ formatNumber(result.opportunity_cost) }} EPV</dd>
      </div>
    </dl>

    <div class="explanation-block">
      <h3>Selected explanation</h3>
      <p>{{ result.selected_explanation }}</p>
    </div>
    <div class="explanation-block">
      <h3>Correct explanation</h3>
      <p>{{ result.correct_explanation }}</p>
    </div>
    <div class="explanation-block">
      <h3>Summary explanation</h3>
      <p>{{ result.summary_explanation }}</p>
    </div>

    <footer class="result-actions">
      <button type="button" @click="emit('retry')">Retry</button>
      <RouterLink class="button secondary-link" :to="`/projects/${projectId}`">Back to project</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.quiz-result-panel {
  display: grid;
  gap: 1rem;
}

.result-banner {
  border-radius: 14px;
  color: white;
  display: grid;
  gap: 0.15rem;
  padding: 1rem;
}

.result-banner.correct {
  background: linear-gradient(135deg, #15803d, #22c55e);
}

.result-banner.incorrect {
  background: linear-gradient(135deg, #9f1239, #f97316);
}

.result-kicker {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.result-banner strong {
  font-size: 1.35rem;
}

.result-metrics {
  display: grid;
  gap: 0.65rem;
  margin: 0;
}

.result-metrics div {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: grid;
  gap: 0.2rem;
  padding: 0.75rem;
}

.result-metrics dt {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.result-metrics dd {
  margin: 0;
}

.explanation-block h3 {
  margin: 0 0 0.25rem;
}

.explanation-block p {
  margin: 0;
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.secondary-link {
  background: #475569;
}
</style>
