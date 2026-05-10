<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { QuizAttemptResponse, QuizPrompt } from '../api/client'
import ArrowDrawingOverlay from '../components/ArrowDrawingOverlay.vue'
import QuizResultPanel from '../components/QuizResultPanel.vue'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{ projectId: string; promptId: string }>()
const projectStore = useProjectStore()
const { ensureProjectHydrated, loading: isHydrating } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const prompt = ref<QuizPrompt | null>(null)
const result = ref<QuizAttemptResponse | null>(null)
const selectedOptionId = ref<string | null>(null)
const isLoadingPrompt = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const imageSrc = computed(() => prompt.value?.image_url || (prompt.value ? apiClient.frameImageUrl(props.projectId, prompt.value.frame_index) : ''))
const selectedOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.selected_option_id) ?? null)
const correctOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.correct_option_id) ?? null)
const correctOptionId = computed(() => result.value?.correct_option_id ?? null)
const incorrectOptionId = computed(() => (result.value && !result.value.is_correct ? result.value.selected_option_id : null))
const isAnswered = computed(() => result.value !== null)
const canSelectArrow = computed(() => !!prompt.value && !isSubmitting.value && !isAnswered.value)

onMounted(async () => {
  await ensureProjectHydrated(props.projectId).catch(() => undefined)
  await loadPrompt()
})

async function loadPrompt() {
  isLoadingPrompt.value = true
  errorMessage.value = ''
  try {
    prompt.value = await apiClient.getQuizPrompt(props.projectId, props.promptId)
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not load quiz prompt.'
  } finally {
    isLoadingPrompt.value = false
  }
}

async function submitAttempt(optionId: string) {
  if (!prompt.value || isSubmitting.value || result.value) return
  selectedOptionId.value = optionId
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    result.value = await apiClient.submitQuizAttempt(props.projectId, prompt.value.prompt_id, { selected_option_id: optionId })
    selectedOptionId.value = result.value.selected_option_id
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not submit quiz attempt.'
  } finally {
    isSubmitting.value = false
  }
}

function retry() {
  result.value = null
  selectedOptionId.value = null
  errorMessage.value = ''
}
</script>

<template>
  <section class="card page-header">
    <RouterLink :to="`/projects/${projectId}`">← Back to project</RouterLink>
    <div>
      <h1>Decision Arrow Quiz</h1>
      <p v-if="prompt" class="muted">Frame {{ prompt.frame_index }} · {{ prompt.timestamp_seconds.toFixed(2) }}s</p>
    </div>
  </section>

  <section v-if="isHydrating || isLoadingPrompt" class="card" aria-live="polite">Loading quiz…</section>
  <section v-if="errorMessage" class="error-card" role="alert">{{ errorMessage }}</section>

  <section v-if="prompt" class="quiz-layout">
    <div class="card prompt-card">
      <div class="question-block">
        <span class="question-kicker">Question</span>
        <h2>{{ prompt.question }}</h2>
        <p v-if="!isAnswered" class="instruction">Click the arrow that represents the best decision.</p>
        <p v-else class="instruction">The correct arrow is highlighted in green. A wrong selected arrow is highlighted in red.</p>
      </div>

      <div class="image-stage">
        <img :src="imageSrc" :alt="`Frame ${prompt.frame_index}`" />
        <ArrowDrawingOverlay
          :options="prompt.options"
          :readonly="true"
          :disabled="!canSelectArrow"
          :selected-option-id="selectedOptionId"
          :correct-option-id="correctOptionId"
          :incorrect-option-id="incorrectOptionId"
          @select-option="submitAttempt"
        />
      </div>
      <p v-if="isSubmitting" class="muted" aria-live="polite">Submitting your answer…</p>
    </div>

    <aside class="card">
      <QuizResultPanel
        v-if="result"
        :project-id="projectId"
        :result="result"
        :selected-option="selectedOption"
        :correct-option="correctOption"
        @retry="retry"
      />
      <div v-else class="pending-result" aria-live="polite">
        <h2>Ready to answer</h2>
        <p class="muted">Select one arrow to create an attempt and reveal correctness, expected value details, and coaching explanations.</p>
        <ul class="option-list">
          <li v-for="option in prompt.options" :key="option.option_id" :class="{ selected: option.option_id === selectedOptionId }">
            <strong>{{ option.option_id }}</strong>
            <span>{{ option.label }}</span>
          </li>
        </ul>
      </div>
    </aside>
  </section>
</template>

<style scoped>
.page-header {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.page-header h1 {
  margin: 0 0 0.25rem;
}

.quiz-layout {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
}

.prompt-card {
  display: grid;
  gap: 1rem;
}

.question-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
}

.question-kicker {
  color: #1f6feb;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.question-block h2 {
  font-size: 1.6rem;
  margin: 0.35rem 0;
}

.instruction {
  color: #334155;
  font-weight: 700;
  margin: 0;
}

.image-stage {
  background: #111827;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.image-stage img {
  display: block;
  width: 100%;
}

.pending-result {
  display: grid;
  gap: 1rem;
}

.pending-result h2 {
  margin: 0;
}

.option-list {
  display: grid;
  gap: 0.6rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.option-list li {
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  gap: 0.65rem;
  padding: 0.75rem;
}

.option-list li.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgb(59 130 246 / 0.16);
}

.option-list strong {
  align-items: center;
  background: #1f6feb;
  border-radius: 999px;
  color: white;
  display: inline-flex;
  height: 2rem;
  justify-content: center;
  width: 2rem;
}

.muted {
  color: #64748b;
}

@media (max-width: 860px) {
  .quiz-layout,
  .page-header {
    display: block;
  }
}
</style>
