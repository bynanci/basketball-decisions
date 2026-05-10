<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { QuizAttemptResponse, QuizPrompt } from '../api/client'
import ArrowDrawingOverlay from '../components/ArrowDrawingOverlay.vue'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{ projectId: string; promptId: string }>()
const projectStore = useProjectStore()
const { ensureProjectHydrated, loading: isHydrating } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const prompt = ref<QuizPrompt | null>(null)
const result = ref<QuizAttemptResponse | null>(null)
const selectedOptionId = ref<string | null>(null)
const imageNaturalWidth = ref(1280)
const imageNaturalHeight = ref(720)
const isSubmitting = ref(false)
const errorMessage = ref('')
const project = computed(() => projectStore.getProject(props.projectId))
const imageSrc = computed(() => prompt.value?.image_url || (prompt.value ? apiClient.frameImageUrl(props.projectId, prompt.value.frame_index) : ''))
const selectedOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.selected_option_id) ?? null)
const correctOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.correct_option_id) ?? null)

onMounted(async () => {
  await ensureProjectHydrated(props.projectId).catch(() => undefined)
  await loadPrompt()
})

function updateImageNaturalSize(event: Event) {
  const image = event.target as HTMLImageElement
  imageNaturalWidth.value = image.naturalWidth || imageNaturalWidth.value
  imageNaturalHeight.value = image.naturalHeight || imageNaturalHeight.value
}

async function loadPrompt() {
  try {
    prompt.value = await apiClient.getQuizPrompt(props.projectId, props.promptId)
    const frame = project.value?.frames.find((item) => item.frame_index === prompt.value?.frame_index)
    if (frame?.width) imageNaturalWidth.value = frame.width
    if (frame?.height) imageNaturalHeight.value = frame.height
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not load quiz prompt.'
  }
}

async function submitAttempt(optionId: string) {
  if (!prompt.value || isSubmitting.value) return
  selectedOptionId.value = optionId
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    result.value = await apiClient.submitQuizAttempt(props.projectId, prompt.value.prompt_id, { selected_option_id: optionId })
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not submit quiz attempt.'
  } finally {
    isSubmitting.value = false
  }
}

function retry() {
  result.value = null
  selectedOptionId.value = null
}
</script>

<template>
  <section class="card">
    <RouterLink :to="`/projects/${projectId}`">← Back to project</RouterLink>
    <h1>Decision Arrow Quiz</h1>
    <p v-if="prompt" class="muted">Frame {{ prompt.frame_index }} · {{ prompt.timestamp_seconds.toFixed(2) }}s</p>
  </section>

  <section v-if="isHydrating" class="card">Loading project…</section>
  <section v-if="errorMessage" class="error-card" role="alert">{{ errorMessage }}</section>

  <section v-if="prompt" class="quiz-layout">
    <div class="card">
      <h2>{{ prompt.question }}</h2>
      <div class="image-stage">
        <img :src="imageSrc" :alt="`Frame ${prompt.frame_index}`" @load="updateImageNaturalSize" />
        <ArrowDrawingOverlay
          :image-natural-width="imageNaturalWidth"
          :image-natural-height="imageNaturalHeight"
          :options="prompt.options"
          :readonly="true"
          :selected-option-id="selectedOptionId"
          @select-option="submitAttempt"
        />
      </div>
      <p class="muted">Click the arrow that represents the best decision.</p>
    </div>

    <aside class="card">
      <h2>Result</h2>
      <p v-if="!result" class="muted">No answer selected yet.</p>
      <div v-else class="result-panel">
        <strong :class="result.is_correct ? 'correct' : 'incorrect'">{{ result.is_correct ? 'Correct' : 'Not quite' }}</strong>
        <p>Selected: {{ selectedOption?.option_id }} — {{ selectedOption?.label }}</p>
        <p>Correct: {{ correctOption?.option_id }} — {{ correctOption?.label }}</p>
        <p v-if="result.opportunity_cost !== null && result.opportunity_cost !== undefined">
          Opportunity cost: {{ result.opportunity_cost.toFixed(2) }} EPV
          <span class="muted">({{ result.selected_expected_value?.toFixed(2) }} vs {{ result.correct_expected_value?.toFixed(2) }})</span>
        </p>
        <h3>Selected explanation</h3>
        <p>{{ result.selected_explanation }}</p>
        <h3>Correct explanation</h3>
        <p>{{ result.correct_explanation }}</p>
        <h3>Coach summary</h3>
        <p>{{ result.summary_explanation }}</p>
        <button type="button" @click="retry">Retry</button>
      </div>
    </aside>
  </section>
</template>

<style scoped>
.quiz-layout {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
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

.correct {
  color: #15803d;
}

.incorrect {
  color: #b45309;
}

.result-panel h3 {
  margin-bottom: 0.25rem;
}

.muted {
  color: #64748b;
}
</style>
