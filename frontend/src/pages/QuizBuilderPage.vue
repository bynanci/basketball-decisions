<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { CourtRoleTarget, DecisionActionType, DecisionArrowPoint, DecisionQuizOption, QuizPromptMode, QuizQuestionMode, SituationType } from '../api/client'
import ArrowDrawingOverlay from '../components/ArrowDrawingOverlay.vue'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'
import { useRoleStore } from '../stores/roleStore'
import { COURT_ROLES, SITUATION_TYPES } from '../types/roles'
import { frameContextTrackIds, nearestSourceTrackIdsForOption, quizBuilderTrackPayload } from '../utils/quizBuilderTracks'

const props = defineProps<{ projectId: string }>()
const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const roleStore = useRoleStore()
const { ensureProjectHydrated, loading: isHydrating } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const question = ref('What is the best decision here?')
const explanation = ref('')
const courtRoleTarget = ref<CourtRoleTarget | ''>(roleStore.roleProfile?.courtRole ?? '')
const situationType = ref<SituationType | ''>(roleStore.roleProfile?.situationTypes[0] ?? '')
const roleInstruction = ref('')
const mode = ref<QuizPromptMode>('STILL_FRAME')
const questionMode = ref<QuizQuestionMode>('FREEZE_FRAME')
const timeLimitMs = ref<number | null>(5000)
const clipStartSec = ref<number | null>(null)
const freezeFrameSec = ref<number | null>(null)
const clipEndSec = ref<number | null>(null)
const options = ref<DecisionQuizOption[]>([])
const selectedOptionId = ref<string | null>(null)
const isSaving = ref(false)
const errorMessage = ref('')
const actionTypes: DecisionActionType[] = ['PASS', 'DRIVE', 'SHOT', 'RESET', 'HOLD']
const questionModes: Array<{ value: QuizQuestionMode; label: string; description: string }> = [
  { value: 'FREEZE_FRAME', label: 'Freeze frame', description: 'No time limit; learners can study the frame and arrows.' },
  { value: 'QUICK_DECISION', label: 'Quick decision', description: 'Learners must answer before the countdown expires.' },
  { value: 'ROLE_READ', label: 'Role read', description: 'Emphasizes role instruction and role-specific attention points.' }
]
const roleFeedbackFields = [
  { key: 'coach', label: 'Coach feedback', placeholder: 'Use this as a skip-pass recognition drill.' },
  { key: 'player', label: 'Player feedback', placeholder: 'Next time, check the low man before committing to the drive.' },
  { key: 'analyst', label: 'Analyst feedback', placeholder: 'Tag this as a missed advantage read before the second-side action.' },
  { key: 'fan', label: 'Fan feedback', placeholder: 'This is why the box score misses decision quality.' }
] as const
const courtRoles = COURT_ROLES as CourtRoleTarget[]
const situationTypes = SITUATION_TYPES as SituationType[]
const project = computed(() => projectStore.getProject(props.projectId))
const frameIndex = computed(() => Number(route.query.frameIndex))
const selectedFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === frameIndex.value) ?? null)
const hasVideoSource = computed(() => project.value?.videoAsset?.source_type === 'upload' && !!project.value.videoAsset.asset_id)
const effectiveMode = computed<QuizPromptMode>(() => (mode.value === 'VIDEO_FREEZE' && hasVideoSource.value ? 'VIDEO_FREEZE' : 'STILL_FRAME'))
const imageSrc = computed(() => (Number.isFinite(frameIndex.value) ? apiClient.frameImageUrl(props.projectId, frameIndex.value) : ''))

const frameTrackIds = computed(() => {
  if (!project.value || !selectedFrame.value) return []
  return frameContextTrackIds(project.value, selectedFrame.value.frame_index)
})
const linkedOptionCount = computed(() => options.value.filter((option) => sourceTrackIdsForOption(option).length > 0).length)
const validationErrors = computed(() => {
  const errors: string[] = []
  if (!selectedFrame.value) errors.push('Select an extracted frame before building a quiz.')
  if (!question.value.trim()) errors.push('Question is required.')
  if (!courtRoleTarget.value) errors.push('Court role is required.')
  if (!situationType.value) errors.push('Situation type is required.')
  if (options.value.length < 2) errors.push('Draw at least 2 arrows.')
  if (options.value.length > 5) errors.push('Use no more than 5 arrows.')
  if (options.value.filter((option) => option.is_correct).length !== 1) errors.push('Mark exactly one option as correct.')
  if (options.value.some((option) => !isNormalizedPoint(option.start) || !isNormalizedPoint(option.end))) errors.push('Every arrow must stay within normalized image coordinates.')
  if (options.value.some((option) => option.expected_value !== null && !Number.isFinite(option.expected_value))) errors.push('Expected values must be valid numbers when provided.')
  if (options.value.some((option) => !option.label.trim() || !option.explanation.trim())) errors.push('Every option needs a label and explanation.')
  if (questionMode.value === 'QUICK_DECISION' && (timeLimitMs.value === null || !Number.isFinite(timeLimitMs.value) || timeLimitMs.value <= 0)) errors.push('Quick decision prompts require a positive time limit.')
  if (effectiveMode.value === 'VIDEO_FREEZE') {
    const freezeAt = freezeFrameSec.value ?? selectedFrame.value?.timestamp_seconds ?? null
    if (freezeAt === null || !Number.isFinite(freezeAt)) errors.push('Freeze frame time is required for video mode.')
    if (clipStartSec.value !== null && (!Number.isFinite(clipStartSec.value) || clipStartSec.value < 0)) errors.push('Clip start must be a non-negative number.')
    if (freezeAt !== null && clipStartSec.value !== null && clipStartSec.value > freezeAt) errors.push('Clip start must be before the freeze frame.')
    if (clipEndSec.value !== null && (!Number.isFinite(clipEndSec.value) || clipEndSec.value < (freezeAt ?? 0))) errors.push('Clip end must be after the freeze frame.')
  }
  if (!explanation.value.trim()) errors.push('Summary explanation is required.')
  return errors
})

onMounted(async () => {
  await ensureProjectHydrated(props.projectId).catch(() => undefined)
  if (selectedFrame.value) {
    freezeFrameSec.value = selectedFrame.value.timestamp_seconds
    clipStartSec.value = Math.max(0, Number((selectedFrame.value.timestamp_seconds - 3).toFixed(2)))
    clipEndSec.value = Number((selectedFrame.value.timestamp_seconds + 1).toFixed(2))
  }
})

function optionId(index: number) {
  return String.fromCharCode(65 + index)
}

function formatSelectLabel(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(' ')
}

function isNormalizedPoint(point: DecisionArrowPoint) {
  return Number.isFinite(point.x) && Number.isFinite(point.y) && point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1
}

function formatExpectedValueInput(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : ''
}

function emptyRoleFeedback() {
  return { coach: '', player: '', analyst: '', fan: '' }
}

function roleFeedbackValue(option: DecisionQuizOption, key: keyof ReturnType<typeof emptyRoleFeedback>) {
  return option.role_feedback?.[key] ?? ''
}

function updateRoleFeedback(option: DecisionQuizOption, key: keyof ReturnType<typeof emptyRoleFeedback>, event: Event) {
  option.role_feedback = { ...(option.role_feedback ?? emptyRoleFeedback()), [key]: (event.target as HTMLTextAreaElement).value }
}

function normalizeRoleFeedback(option: DecisionQuizOption) {
  const feedback = option.role_feedback ?? emptyRoleFeedback()
  const normalized = {
    coach: feedback.coach?.trim() || null,
    player: feedback.player?.trim() || null,
    analyst: feedback.analyst?.trim() || null,
    fan: feedback.fan?.trim() || null
  }
  return Object.values(normalized).some(Boolean) ? normalized : null
}

function sourceTrackIdsForOption(option: DecisionQuizOption) {
  if (!project.value || !selectedFrame.value) return option.source_track_ids ?? []
  return nearestSourceTrackIdsForOption(project.value, selectedFrame.value, option.start, option.source_track_ids ?? [])
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
    explanation: '',
    role_feedback: emptyRoleFeedback()
  })
  selectedOptionId.value = id
  errorMessage.value = ''
}

function setCorrect(optionIdToMark: string) {
  options.value = options.value.map((option) => ({ ...option, is_correct: option.option_id === optionIdToMark }))
}

function updateExpectedValue(option: DecisionQuizOption, event: Event) {
  const value = (event.target as HTMLInputElement).value
  if (value.trim() === '') {
    option.expected_value = null
    return
  }
  const parsed = Number(value)
  option.expected_value = Number.isFinite(parsed) ? parsed : null
}

async function savePrompt() {
  if (!selectedFrame.value || !courtRoleTarget.value || !situationType.value || validationErrors.value.length || isSaving.value) return
  const selectedCourtRole = courtRoleTarget.value
  const selectedSituationType = situationType.value
  isSaving.value = true
  errorMessage.value = ''
  try {
    const sanitizedOptions = options.value.map((option) => ({
      ...option,
      label: option.label.trim(),
      explanation: option.explanation.trim(),
      role_feedback: normalizeRoleFeedback(option)
    }))
    const trackPayload = project.value
      ? quizBuilderTrackPayload(project.value, selectedFrame.value, sanitizedOptions)
      : { context_track_ids: [], source_track_ids: [], options: sanitizedOptions.map((option) => ({ ...option, source_track_ids: option.source_track_ids ?? [] })) }
    const prompt = await apiClient.createQuizPrompt(props.projectId, {
      question: question.value,
      court_role_target: selectedCourtRole,
      situation_type: selectedSituationType,
      user_role_targets: [selectedCourtRole],
      role_instruction: roleInstruction.value.trim() || null,
      frame_id: selectedFrame.value.frame_id,
      frame_index: selectedFrame.value.frame_index,
      timestamp_seconds: selectedFrame.value.timestamp_seconds,
      image_url: imageSrc.value,
      image_path: selectedFrame.value.image_path,
      video_asset_id: effectiveMode.value === 'VIDEO_FREEZE' ? project.value?.videoAsset?.asset_id ?? null : null,
      clip_start_seconds: effectiveMode.value === 'VIDEO_FREEZE' ? clipStartSec.value : null,
      freeze_frame_seconds: effectiveMode.value === 'VIDEO_FREEZE' ? freezeFrameSec.value : null,
      clip_end_seconds: effectiveMode.value === 'VIDEO_FREEZE' ? clipEndSec.value : null,
      mode: effectiveMode.value,
      question_mode: questionMode.value,
      time_limit_ms: questionMode.value === 'QUICK_DECISION' ? timeLimitMs.value : null,
      context_track_ids: trackPayload.context_track_ids,
      source_track_ids: trackPayload.source_track_ids,
      options: trackPayload.options,
      explanation: explanation.value.trim()
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
        <img :src="imageSrc" :alt="`Frame ${selectedFrame.frame_index}`" />
        <ArrowDrawingOverlay
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

      <h2>Role context</h2>
      <label>
        Court role
        <select v-model="courtRoleTarget">
          <option value="" disabled>Select a court role</option>
          <option v-for="role in courtRoles" :key="role" :value="role">{{ formatSelectLabel(role) }}</option>
        </select>
      </label>
      <label>
        Situation type
        <select v-model="situationType">
          <option value="" disabled>Select a situation type</option>
          <option v-for="situation in situationTypes" :key="situation" :value="situation">{{ formatSelectLabel(situation) }}</option>
        </select>
      </label>
      <label>
        Role instruction
        <textarea v-model="roleInstruction" placeholder="You are the ball handler. Read the help defender and choose the best next action."></textarea>
      </label>

      <h2>Question mode</h2>
      <label>
        Interaction style
        <select v-model="questionMode">
          <option v-for="item in questionModes" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <p class="muted">{{ questionModes.find((item) => item.value === questionMode)?.description }}</p>
      <label v-if="questionMode === 'QUICK_DECISION'">
        Time limit (milliseconds)
        <input v-model.number="timeLimitMs" type="number" min="1" step="100" />
      </label>

      <h2>Playback mode</h2>
      <label>
        Media playback
        <select v-model="mode">
          <option value="STILL_FRAME">Still frame</option>
          <option value="VIDEO_FREEZE" :disabled="!hasVideoSource">Video freeze</option>
        </select>
      </label>
      <p v-if="!hasVideoSource" class="muted">Upload a local MP4 to enable video-freeze prompts. This prompt will save as a still frame.</p>
      <div v-if="effectiveMode === 'VIDEO_FREEZE'" class="time-grid">
        <label>Clip start (seconds)<input v-model.number="clipStartSec" type="number" min="0" step="0.1" /></label>
        <label>Freeze frame (seconds)<input v-model.number="freezeFrameSec" type="number" min="0" step="0.1" /></label>
        <label>Clip end (seconds)<input v-model.number="clipEndSec" type="number" min="0" step="0.1" /></label>
      </div>

      <h2>Options</h2>
      <p class="muted">Manual expected value is temporary until EPV model exists.</p>
      <p class="muted">Context tracks are all players visible in this frame. Source tracks identify the player(s) directly involved in the selected decision and are used for Player Value.</p>
      <p v-if="options.length && linkedOptionCount === 0" class="warning-text">This prompt can still be used for decision training, but Player Value may fall back to UNKNOWN.</p>
      <article v-for="option in options" :key="option.option_id" :class="['option-card', { selected: option.option_id === selectedOptionId }]">
        <header>
          <strong>{{ option.option_id }}</strong>
          <label class="radio-row"><input type="radio" name="correct" :checked="option.is_correct" @change="setCorrect(option.option_id)" /> Correct</label>
        </header>
        <label>Label <input v-model="option.label" /></label>
        <label>Action type <select v-model="option.action_type"><option v-for="action in actionTypes" :key="action" :value="action">{{ action }}</option></select></label>
        <label>Expected value (optional, recommended) <input type="number" step="0.01" :value="formatExpectedValueInput(option.expected_value)" @input="updateExpectedValue(option, $event)" /></label>
        <label>Option explanation <textarea v-model="option.explanation" placeholder="What does this option create or miss?"></textarea></label>
        <p class="muted">Linked source track: {{ sourceTrackIdsForOption(option).join(', ') || 'none' }}</p>
        <details class="role-feedback-panel">
          <summary>Role-specific feedback (optional)</summary>
          <p class="muted">Leave blank to fall back to the general option explanation.</p>
          <label v-for="field in roleFeedbackFields" :key="field.key">
            {{ field.label }}
            <textarea :value="roleFeedbackValue(option, field.key)" :placeholder="field.placeholder" @input="updateRoleFeedback(option, field.key, $event)"></textarea>
          </label>
        </details>
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

.time-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.role-feedback-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  margin-top: 0.75rem;
  padding: 0.75rem;
}

.role-feedback-panel summary {
  cursor: pointer;
  font-weight: 800;
}

.validation-list {
  color: #991b1b;
}

.muted {
  color: #64748b;
}

.warning-text {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  color: #92400e;
  padding: 0.75rem;
}
</style>
