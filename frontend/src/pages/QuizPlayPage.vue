<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
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
const videoElement = ref<HTMLVideoElement | null>(null)
const isVideoAtFreeze = ref(false)
const videoPlaybackMessage = ref('')
const videoSourceFailed = ref(false)
const imageSrc = computed(() => prompt.value?.image_url || (prompt.value ? apiClient.frameImageUrl(props.projectId, prompt.value.frame_index) : ''))
const videoSrc = computed(() => apiClient.videoSourceUrl(props.projectId))
const freezeTime = computed(() => prompt.value?.freeze_frame_seconds ?? prompt.value?.timestamp_seconds ?? 0)
const clipStart = computed(() => Math.max(0, prompt.value?.clip_start_seconds ?? Math.max(0, freezeTime.value - 3)))
const isVideoPrompt = computed(() => prompt.value?.mode === 'VIDEO_FREEZE')
const isAnswered = computed(() => result.value !== null)
const canUseVideo = computed(() => isVideoPrompt.value && !videoSourceFailed.value)
const shouldShowArrows = computed(() => !canUseVideo.value || isVideoAtFreeze.value || isAnswered.value)
const fallbackMessage = computed(() =>
  isVideoPrompt.value && videoSourceFailed.value
    ? 'Video playback is unavailable for this prompt, so the still frame is shown instead.'
    : ''
)
const selectedOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.selected_option_id) ?? null)
const correctOption = computed(() => prompt.value?.options.find((option) => option.option_id === result.value?.correct_option_id) ?? null)
const correctOptionId = computed(() => result.value?.correct_option_id ?? null)
const incorrectOptionId = computed(() => (result.value && !result.value.is_correct ? result.value.selected_option_id : null))
const canSelectArrow = computed(() => !!prompt.value && shouldShowArrows.value && !isSubmitting.value && !isAnswered.value)
const roleInstruction = computed(() => prompt.value?.role_instruction?.trim() ?? '')

onMounted(async () => {
  await ensureProjectHydrated(props.projectId).catch(() => undefined)
  await loadPrompt()
})

async function loadPrompt() {
  isLoadingPrompt.value = true
  errorMessage.value = ''
  try {
    prompt.value = await apiClient.getQuizPrompt(props.projectId, props.promptId)
    if (prompt.value.mode === 'VIDEO_FREEZE') {
      await nextTick()
      startVideoClip()
    }
  } catch (error) {
    errorMessage.value = isApiClientError(error) ? error.message : 'Could not load quiz prompt.'
  } finally {
    isLoadingPrompt.value = false
  }
}

function startVideoClip() {
  const video = videoElement.value
  if (!video || !prompt.value) return
  isVideoAtFreeze.value = false
  videoPlaybackMessage.value = 'Playing clip… arrows appear at the freeze.'
  video.currentTime = clipStart.value
  const playPromise = video.play()
  if (playPromise) {
    playPromise.catch(() => {
      videoPlaybackMessage.value = 'Press play to start the clip. It will pause at the freeze.'
    })
  }
}

function handleVideoLoadedMetadata() {
  startVideoClip()
}

function handleVideoTimeUpdate() {
  const video = videoElement.value
  if (!video || !prompt.value || isVideoAtFreeze.value) return
  if (video.currentTime >= freezeTime.value) {
    video.pause()
    video.currentTime = freezeTime.value
    isVideoAtFreeze.value = true
    videoPlaybackMessage.value = 'Paused at the freeze. Select the best decision arrow.'
  }
}

function handleVideoError() {
  videoSourceFailed.value = true
  isVideoAtFreeze.value = true
  videoPlaybackMessage.value = ''
}

function replayClip() {
  if (!canUseVideo.value) return
  startVideoClip()
}

async function submitAttempt(optionId: string) {
  if (!prompt.value || isSubmitting.value || result.value || !shouldShowArrows.value) return
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
        <p v-if="roleInstruction" class="role-instruction">{{ roleInstruction }}</p>
        <h2>{{ prompt.question }}</h2>
        <p v-if="!isAnswered" class="instruction">{{ canUseVideo && !isVideoAtFreeze ? 'Watch the clip until it freezes, then click the best decision arrow.' : 'Click the arrow that represents the best decision.' }}</p>
        <p v-else class="instruction">The correct arrow is highlighted in green. A wrong selected arrow is highlighted in red.</p>
      </div>

      <p v-if="fallbackMessage" class="fallback-banner" role="status">{{ fallbackMessage }}</p>
      <div class="image-stage">
        <video
          v-if="canUseVideo"
          ref="videoElement"
          :src="videoSrc"
          playsinline
          muted
          controls
          preload="metadata"
          @loadedmetadata="handleVideoLoadedMetadata"
          @timeupdate="handleVideoTimeUpdate"
          @error="handleVideoError"
        ></video>
        <img v-else :src="imageSrc" :alt="`Frame ${prompt.frame_index}`" />
        <ArrowDrawingOverlay
          v-if="shouldShowArrows"
          :options="prompt.options"
          :readonly="true"
          :disabled="!canSelectArrow"
          :selected-option-id="selectedOptionId"
          :correct-option-id="correctOptionId"
          :incorrect-option-id="incorrectOptionId"
          @select-option="submitAttempt"
        />
      </div>
      <div v-if="canUseVideo" class="video-controls">
        <button type="button" @click="replayClip">Replay clip</button>
        <span class="muted" aria-live="polite">{{ videoPlaybackMessage }}</span>
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
        :options="prompt.options"
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

.role-instruction {
  background: #eff6ff;
  border-left: 4px solid #1f6feb;
  border-radius: 10px;
  color: #1e3a8a;
  font-weight: 700;
  margin: 0.75rem 0;
  padding: 0.75rem 1rem;
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

.fallback-banner {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 12px;
  color: #9a3412;
  font-weight: 700;
  margin: 0;
  padding: 0.75rem;
}

.image-stage {
  background: #111827;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.image-stage img,
.image-stage video {
  display: block;
  width: 100%;
}

.video-controls {
  align-items: center;
  display: flex;
  gap: 0.75rem;
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
