<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { DecisionQuizOption, QuizAttemptResponse } from '../api/client'
import { useRoleStore } from '../stores/roleStore'
import { formatResultNumber, formatScore, isFiniteNumber } from './quizResultFormatting'

const roleStore = useRoleStore()

const props = defineProps<{
  projectId: string
  result: QuizAttemptResponse
  selectedOption?: DecisionQuizOption | null
  correctOption?: DecisionQuizOption | null
  options?: DecisionQuizOption[]
}>()

const emit = defineEmits<{
  (event: 'retry'): void
}>()

const selectedOptionLabel = computed(() => formatOption(props.selectedOption, props.result.selected_option_id))
const correctOptionLabel = computed(() => formatOption(props.correctOption, props.result.correct_option_id))
const hasSelectedExpectedValue = computed(() => isFiniteNumber(props.result.selected_expected_value))
const hasCorrectExpectedValue = computed(() => isFiniteNumber(props.result.correct_expected_value))
const hasOpportunityCost = computed(() => isFiniteNumber(props.result.opportunity_cost))
const scoringModeLabel = computed(() => props.result.scoring_mode === 'EXPECTED_VALUE' ? 'Expected value' : 'Correctness only')
const epvOptions = computed(() => props.options ?? [])
const hasEpvComparison = computed(() => epvOptions.value.length > 0 && epvOptions.value.every((option) => isFiniteNumber(option.expected_value)))
const userRoleLabel = computed(() => formatUserRole(roleStore.roleProfile?.userRole ?? 'selected role'))
const selectedRoleFeedback = computed(() => props.result.selected_role_feedback?.trim() || props.result.selected_explanation || 'No feedback available.')
const correctRoleFeedback = computed(() => props.result.correct_role_feedback?.trim() || props.result.correct_explanation || 'No feedback available.')

function formatOption(option: DecisionQuizOption | null | undefined, fallbackOptionId: string) {
  if (!option) return fallbackOptionId
  const label = option.label.trim() || 'Decision'
  return `${option.option_id} — ${label}`
}

function formatUserRole(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
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
      <div class="score-metric">
        <dt>Score</dt>
        <dd>{{ formatScore(result.score) }}</dd>
      </div>
      <div>
        <dt>Scoring mode</dt>
        <dd>{{ scoringModeLabel }}</dd>
      </div>
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
        <dd>{{ formatResultNumber(result.selected_expected_value) }}</dd>
      </div>
      <div v-if="hasCorrectExpectedValue">
        <dt>Correct expected value</dt>
        <dd>{{ formatResultNumber(result.correct_expected_value) }}</dd>
      </div>
      <div v-if="hasOpportunityCost">
        <dt>Opportunity cost</dt>
        <dd>{{ formatResultNumber(result.opportunity_cost) }} EPV</dd>
      </div>
    </dl>

    <section v-if="hasEpvComparison" class="epv-comparison" aria-labelledby="epv-comparison-title">
      <h3 id="epv-comparison-title">EPV comparison</h3>
      <ol>
        <li v-for="option in epvOptions" :key="option.option_id" :class="{ selected: option.option_id === result.selected_option_id, correct: option.option_id === result.correct_option_id }">
          <span><strong>{{ option.option_id }}</strong> {{ option.label }}</span>
          <span class="epv-value">{{ formatResultNumber(option.expected_value) }}</span>
          <small v-if="option.option_id === result.selected_option_id">Selected</small>
          <small v-if="option.option_id === result.correct_option_id">Correct</small>
        </li>
      </ol>
    </section>

    <section class="feedback-section" aria-labelledby="general-feedback-title">
      <h3 id="general-feedback-title">General explanation</h3>
      <div class="explanation-block">
        <h4>Selected option</h4>
        <p>{{ result.selected_explanation || 'No explanation available.' }}</p>
      </div>
      <div class="explanation-block">
        <h4>Correct option</h4>
        <p>{{ result.correct_explanation || 'No explanation available.' }}</p>
      </div>
      <div class="explanation-block">
        <h4>Summary</h4>
        <p>{{ result.summary_explanation || 'No summary available.' }}</p>
      </div>
    </section>

    <section class="feedback-section role-feedback-block" aria-labelledby="role-feedback-title">
      <h3 id="role-feedback-title">{{ userRoleLabel }} feedback</h3>
      <div class="explanation-block">
        <h4>Selected option</h4>
        <p>{{ selectedRoleFeedback }}</p>
      </div>
      <div class="explanation-block">
        <h4>Correct option</h4>
        <p>{{ correctRoleFeedback }}</p>
      </div>
    </section>

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

.result-metrics .score-metric {
  background: #ecfdf5;
  border-color: #86efac;
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

.epv-comparison {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 0.9rem;
}

.epv-comparison h3 {
  margin: 0 0 0.6rem;
}

.epv-comparison ol {
  display: grid;
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.epv-comparison li {
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: grid;
  gap: 0.35rem;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  padding: 0.65rem;
}

.epv-comparison li.selected {
  border-color: #f97316;
}

.epv-comparison li.correct {
  border-color: #22c55e;
}

.epv-value {
  font-weight: 800;
}

.feedback-section {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: grid;
  gap: 0.75rem;
  padding: 0.9rem;
}

.feedback-section h3 {
  margin: 0;
}

.role-feedback-block {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.explanation-block h4 {
  color: #475569;
  font-size: 0.8rem;
  margin: 0 0 0.25rem;
  text-transform: uppercase;
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
