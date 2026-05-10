<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { DecisionActionType, DecisionArrowPoint, DecisionQuizOption } from '../api/client'
import ArrowDrawingOverlay from '../components/ArrowDrawingOverlay.vue'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{ projectId: string }>()
const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const { ensureProjectHydrated, loading: isHydrating } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const question = ref('What is the best decision here?')
const explanation = ref('')
const options = ref<DecisionQuizOption[]>([])
const selectedOptionId = ref<string | null>(null)
const imageNaturalWidth = ref(1280)
const imageNaturalHeight = ref(720)
const isSaving = ref(false)
const errorMessage = ref('')
const actionTypes: DecisionActionType[] = ['PASS', 'DRIVE', 'SHOT', 'RESET', 'HOLD']
const project = computed(() => projectStore.getProject(props.projectId))
const frameIndex = computed(() => Number(route.query.frameIndex))
const selectedFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === frameIndex.value) ?? null)
const imageSrc = computed(() => (Number.isFinite(frameIndex.value) ? apiClient.frameImageUrl(props.projectId, frameIndex.value) : ''))
const validationErrors = computed(() => {
  const errors: string[] = []
  if (!selectedFrame.value) errors.push('Select an extracted frame before building a quiz.')
  if (!question.value.trim()) errors.push('Question is required.')
  if (options.value.length < 2) errors.push('Draw at least 2 arrows.')
  if (options.value.length > 5) errors.push('Use no more than 5 arrows.')
  if (options.value.filter((option) => option.is_correct).length !== 1) errors.push('Mark exactly one option as correct.')
  if (options.value.some((option) => !option.label.trim() || !option.explanation.trim())) errors.push('Every option needs a label and explanation.')
  if (!explanation.value.trim()) errors.push('Summary explanation is required.')
  return errors
})

onMounted(async () => {
  await ensureProjectHydrated(props.projectId).catch(() => undefined)
  if (selectedFrame.value?.width) imageNaturalWidth.value = selectedFrame.value.width
  if (selectedFrame.value?.height) imageNaturalHeight.value = selectedFrame.value.height
})

function updateImageNaturalSize(event: Event) {
  const image = event.target as HTMLImageElement
  imageNaturalWidth.value = image.naturalWidth || imageNaturalWidth.value
  imageNaturalHeight.value = image.naturalHeight || imageNaturalHeight.value
}

function optionId(index: number) {
  return String.fromCharCode(65 + index)
}

function createOption(payload: { start: DecisionArrowPoint; end: DecisionArrowPoint }) {
  if (options.value.length >= 5) {
    errorMessage.value = 'Maximum 5 arrows per prompt.'
    return
  }
  const id = optionId(options.value.length)
  options.value.push({
    option_id: id,
    label: `Option ${id}`,
    action_type: 'PASS',
    start: payload.start,
    end: payload.end,
    expected_value: null,
    is_correct: options.value.length === 0,
    explanation: ''
  })
  selectedOptionId.value = id
  errorMessage.value = ''
}

function setCorrect(optionIdToMark: string) {
  options.value = options.value.map((option) => ({ ...option, is_correct: option.option_id === optionIdToMark }))
}

function updateExpectedValue(option: DecisionQuizOption, event: Event) {
  const value = (event.target as HTMLInputElement).value
  option.expected_value = value.trim() === '' ? null : Number(value)
}

async function savePrompt() {
  if (!selectedFrame.value || validationErrors.value.length || isSaving.value) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    const prompt = await apiClient.createQuizPrompt(props.projectId, {
      question: question.value,
      frame_id: selectedFrame.value.frame_id,
      frame_index: selectedFrame.value.frame_index,
      timestamp_seconds: selectedFrame.value.timestamp_seconds,
      image_url: imageSrc.value,
      image_path: selectedFrame.value.image_path,
      options: options.value,
      explanation: explanation.value
    })
    await router.push(`/projects/${props.projectId}/quiz/${prompt.prompt_id}`)
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not save quiz prompt.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="card">
    <RouterLink :to="`/projects/${projectId}`">← Back to project</RouterLink>
    <h1>Decision Arrow Quiz Builder</h1>
    <p class="muted">Draw 2–5 arrows on one extracted frame, label them, and mark the best decision.</p>
  </section>

  <section v-if="isHydrating" class="card">Loading project…</section>
  <section v-if="errorMessage" class="error-card" role="alert">{{ errorMessage }}</section>

  <section v-if="!selectedFrame" class="error-card" role="alert">
    No extracted frame was selected. Open this page from a frame card on the project page.
  </section>

  <section v-else class="builder-layout">
    <div class="card">
      <h2>Frame {{ selectedFrame.frame_index }} · {{ selectedFrame.timestamp_seconds.toFixed(2) }}s</h2>
      <div class="image-stage">
        <img :src="imageSrc" :alt="`Frame ${selectedFrame.frame_index}`" @load="updateImageNaturalSize" />
        <ArrowDrawingOverlay
          :image-natural-width="imageNaturalWidth"
          :image-natural-height="imageNaturalHeight"
          :options="options"
          :selected-option-id="selectedOptionId"
          @create-arrow="createOption"
          @select-option="selectedOptionId = $event"
        />
      </div>
      <p class="muted">Click and drag over the image to add an arrow. Click an existing arrow to select it.</p>
    </div>

    <div class="card">
      <label>
        Question
        <input v-model="question" placeholder="What should the ball handler do?" />
      </label>
      <label>
        Summary explanation
        <textarea v-model="explanation" placeholder="Explain why the correct decision is best."></textarea>
      </label>

      <h2>Options</h2>
      <article v-for="option in options" :key="option.option_id" :class="['option-card', { selected: option.option_id === selectedOptionId }]">
        <header>
          <strong>{{ option.option_id }}</strong>
          <label class="radio-row"><input type="radio" name="correct" :checked="option.is_correct" @change="setCorrect(option.option_id)" /> Correct</label>
        </header>
        <label>Label <input v-model="option.label" /></label>
        <label>Action type <select v-model="option.action_type"><option v-for="action in actionTypes" :key="action" :value="action">{{ action }}</option></select></label>
        <label>Expected value (optional) <input type="number" step="0.01" :value="option.expected_value ?? ''" @input="updateExpectedValue(option, $event)" /></label>
        <label>Option explanation <textarea v-model="option.explanation" placeholder="What does this option create or miss?"></textarea></label>
      </article>
      <p v-if="!options.length" class="muted">No arrows yet.</p>

      <ul v-if="validationErrors.length" class="validation-list">
        <li v-for="validationError in validationErrors" :key="validationError">{{ validationError }}</li>
      </ul>
      <button type="button" :disabled="validationErrors.length > 0 || isSaving" @click="savePrompt">{{ isSaving ? 'Saving…' : 'Save quiz prompt' }}</button>
    </div>
  </section>
</template>

<style scoped>
.builder-layout {
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

textarea,
select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  display: block;
  margin: 0.5rem 0 1rem;
  padding: 0.75rem;
  width: min(100%, 520px);
}

textarea {
  min-height: 90px;
}

.option-card {
  border: 1px solid #dde3ee;
  border-radius: 12px;
  margin-bottom: 1rem;
  padding: 1rem;
}

.option-card.selected {
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgb(34 197 94 / 0.16);
}

.option-card header,
.radio-row {
  align-items: center;
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
}

.radio-row input {
  display: inline;
  margin: 0;
  width: auto;
}

.validation-list {
  color: #991b1b;
}

.muted {
  color: #64748b;
}
</style>
