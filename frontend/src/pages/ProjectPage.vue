<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { DecisionDiagnosticsReport, LeagueTag, QuizPrompt, SourceLicenseType, UsageScope, VideoSourceRecord } from '../api/client'
import Court2DView from '../components/Court2DView.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
const { ensureProjectHydrated, isHydrating, hydrationError, hydrationErrorCode, hydrationErrorHint } = useProjectHydration()
projectStore.setActiveProject(props.projectId)
const project = computed(() => projectStore.getProject(props.projectId))
const isExtracting = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')
const hasCalibration = computed(() => !!project.value?.calibration)
const hasTracking = computed(() => !!project.value && (project.value.detections.length > 0 || project.value.tracks.length > 0 || project.value.projectedTracks.length > 0))
const hasProjectedTracks = computed(() => (project.value?.projectedTracks.length ?? 0) > 0)
const isSampleProject = computed(() => project.value?.source === 'sample')
const aliasCount = computed(() => project.value?.playerAliases?.aliases.length ?? 0)
const aliasedTrackCount = computed(() => new Set(project.value?.playerAliases?.aliases.flatMap((alias) => alias.track_ids) ?? []).size)
const unaliasedTrackCount = computed(() => Math.max((project.value?.tracks.length ?? 0) - aliasedTrackCount.value, 0))
const quizPrompts = ref<QuizPrompt[]>([])
const decisionDiagnostics = ref<DecisionDiagnosticsReport | null>(null)
const isLoadingQuizPrompts = ref(false)
const quizErrorMessage = ref('')
const quizErrorCode = ref('')
const quizErrorHint = ref('')

const licenseOptions: SourceLicenseType[] = ['OWNED', 'PERMISSION_GRANTED', 'PUBLIC_DOMAIN', 'CREATIVE_COMMONS', 'RESEARCH_DATASET', 'YOUTUBE_REFERENCE_ONLY', 'UNKNOWN']
const usageScopeOptions: UsageScope[] = ['TRAINING', 'EVALUATION', 'REFERENCE_ONLY', 'DEMO_ONLY']
const leagueTagOptions: LeagueTag[] = ['NBA', 'EUROLEAGUE', 'NCAA', 'LOCAL', 'OTHER', 'UNKNOWN']
const isSavingSource = ref(false)
const sourceSaveMessage = ref('')
const sourceForm = ref<VideoSourceRecord | null>(null)
const sourceValidationHint = computed(() => {
  const source = sourceForm.value
  if (!source) return ''
  if (source.allowed_for_training && ['UNKNOWN', 'YOUTUBE_REFERENCE_ONLY'].includes(source.license_type)) return 'Training requires a license other than UNKNOWN or YOUTUBE_REFERENCE_ONLY.'
  if (source.allowed_for_training && !source.rights_confirmed) return 'Training requires rights confirmation.'
  if (source.allowed_for_training && source.usage_scope === 'REFERENCE_ONLY') return 'Reference-only sources cannot be used for training.'
  return ''
})
const canSaveSource = computed(() => !!sourceForm.value && !sourceValidationHint.value && !isSavingSource.value)

function cloneSource(source?: VideoSourceRecord | null) {
  sourceForm.value = source ? { ...source } : null
}

watch(() => project.value?.sourceGovernance, (source) => cloneSource(source), { immediate: true })

onMounted(() => {
  void ensureProjectHydrated(props.projectId, { force: true }).catch(() => undefined)
  void loadQuizPrompts()
  void loadDecisionDiagnostics()
})

function showError(error: unknown) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'FRAME_EXTRACTION_ERROR'
    errorMessage.value = 'Could not extract frames.'
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

async function loadQuizPrompts() {
  isLoadingQuizPrompts.value = true
  quizErrorMessage.value = ''
  quizErrorCode.value = ''
  quizErrorHint.value = ''
  try {
    quizPrompts.value = await apiClient.listQuizPrompts(props.projectId)
  } catch (error) {
    quizPrompts.value = []
    if (isApiClientError(error)) {
      quizErrorCode.value = error.code
      quizErrorMessage.value = error.message
      quizErrorHint.value = error.debug_hint ?? ''
    } else {
      quizErrorCode.value = 'QUIZ_PROMPTS_LOAD_ERROR'
      quizErrorMessage.value = 'Could not load quiz prompts.'
      quizErrorHint.value = error instanceof Error ? error.message : ''
    }
  } finally {
    isLoadingQuizPrompts.value = false
  }
}


async function loadDecisionDiagnostics() {
  try {
    decisionDiagnostics.value = await apiClient.getDecisionDiagnostics()
  } catch {
    decisionDiagnostics.value = null
  }
}

function promptDifficulty(prompt: QuizPrompt) {
  return decisionDiagnostics.value?.prompt_diagnostics.find(
    (diagnostic) => diagnostic.project_id === prompt.project_id && diagnostic.prompt_id === prompt.prompt_id
  )?.difficulty ?? 'NOT_BUILT'
}

function promptDifficultyLabel(prompt: QuizPrompt) {
  const difficulty = promptDifficulty(prompt)
  return difficulty === 'NOT_BUILT' ? 'Diagnostics not built' : difficulty.replace(/_/g, ' ')
}

function hasPromptExpectedValues(prompt: QuizPrompt) {
  return prompt.options.length > 0 && prompt.options.every((option) => typeof option.expected_value === 'number' && Number.isFinite(option.expected_value))
}

async function extractFrames() {
  const videoAsset = project.value?.videoAsset
  if (!videoAsset || isExtracting.value) return
  isExtracting.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const response = await apiClient.extractFrames(props.projectId, {
      project_id: props.projectId,
      video_asset_id: videoAsset.asset_id,
      target_fps: 1,
      max_frames: 120
    })
    projectStore.setFrames(props.projectId, response.frames)
  } catch (error) {
    showError(error)
  } finally {
    isExtracting.value = false
  }
}
async function saveSourceGovernance() {
  if (!sourceForm.value || !canSaveSource.value) return
  isSavingSource.value = true
  sourceSaveMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.updateProjectSource(props.projectId, sourceForm.value)
    projectStore.setSourceGovernance(props.projectId, response)
    cloneSource(response)
    sourceSaveMessage.value = 'Source governance saved.'
  } catch (error) {
    showError(error)
  } finally {
    isSavingSource.value = false
  }
}

</script>

<template>
  <section class="card">
    <h1>{{ project?.name ?? 'Project' }} <span v-if="isSampleProject" class="sample-badge">Sample</span></h1>
    <p>Project id: {{ projectId }}</p>
    <p>Source: {{ project?.source ?? 'unknown' }} <span v-if="project?.videoFileName">· {{ project.videoFileName }}</span></p>
    <RouterLink class="button" :to="`/projects/${projectId}/pipeline`">Open pipeline</RouterLink>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/calibration`">Calibrate court</RouterLink>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Tracking</RouterLink>
    <RouterLink v-if="hasTracking" class="button secondary" :to="`/projects/${projectId}/tracking-review`">Tracking Review</RouterLink>
  </section>

  <section v-if="isHydrating" class="card" aria-live="polite">
    <strong>Loading project…</strong>
    <p>Recovering project metadata and saved pipeline artifacts from backend storage.</p>
  </section>

  <section v-if="hydrationError" class="error-card" role="alert">
    <strong>{{ hydrationErrorCode }}</strong>
    <p>{{ hydrationError }}</p>
    <small v-if="hydrationErrorHint">{{ hydrationErrorHint }}</small>
  </section>

  <section v-if="errorMessage" class="error-card" role="alert">
    <strong>{{ errorCode }}</strong>
    <p>{{ errorMessage }}</p>
    <small v-if="errorHint">{{ errorHint }}</small>
  </section>


  <section class="card source-governance-card">
    <div class="section-header">
      <div>
        <p class="eyebrow">Data Source Governance</p>
        <h2>Source Governance</h2>
      </div>
      <span v-if="project?.sourceGovernance?.usage_scope === 'REFERENCE_ONLY'" class="warning-badge">Reference only</span>
    </div>
    <p class="muted">Dataset exports only include projects whose source is explicitly allowed for training.</p>
    <p v-if="!sourceForm" class="muted">No source governance record exists yet. Upload or import a video, then review the source policy.</p>
    <form v-else class="source-form" @submit.prevent="saveSourceGovernance">
      <label>
        License type
        <select v-model="sourceForm.license_type">
          <option v-for="option in licenseOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
      <label>
        Usage scope
        <select v-model="sourceForm.usage_scope">
          <option v-for="option in usageScopeOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
      <label>
        League tag
        <select v-model="sourceForm.league_tag">
          <option v-for="option in leagueTagOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
      <label class="checkbox-label"><input v-model="sourceForm.rights_confirmed" type="checkbox" /> Rights confirmed</label>
      <label class="checkbox-label"><input v-model="sourceForm.allowed_for_training" type="checkbox" /> Allowed for training</label>
      <label class="checkbox-label"><input v-model="sourceForm.allowed_for_local_storage" type="checkbox" /> Allowed for local storage</label>
      <label class="full-width">
        Notes
        <textarea v-model="sourceForm.notes" rows="3" placeholder="Record permissions, source context, or license notes." />
      </label>
      <p v-if="sourceValidationHint" class="error-text">{{ sourceValidationHint }}</p>
      <p v-if="sourceSaveMessage" class="success-message">{{ sourceSaveMessage }}</p>
      <button type="submit" :disabled="!canSaveSource">{{ isSavingSource ? 'Saving…' : 'Save source governance' }}</button>
    </form>
  </section>

  <section class="grid">
    <div class="card">
      <h2>Video</h2>
      <dl v-if="project?.videoAsset" class="metadata-list">
        <div><dt>Asset</dt><dd>{{ project.videoAsset.asset_id }}</dd></div>
        <div><dt>Source</dt><dd>{{ project.videoAsset.source_type }}</dd></div>
        <div v-if="project.videoAsset.filename"><dt>File</dt><dd>{{ project.videoAsset.filename }}</dd></div>
        <div v-if="project.videoAsset.width && project.videoAsset.height"><dt>Size</dt><dd>{{ project.videoAsset.width }} × {{ project.videoAsset.height }}</dd></div>
        <div v-if="project.videoAsset.duration_seconds"><dt>Duration</dt><dd>{{ project.videoAsset.duration_seconds.toFixed(2) }}s</dd></div>
        <div v-if="project.videoAsset.fps"><dt>FPS</dt><dd>{{ project.videoAsset.fps }}</dd></div>
        <div v-if="project.videoAsset.frame_count"><dt>Frames</dt><dd>{{ project.videoAsset.frame_count }}</dd></div>
      </dl>
      <VideoPlayer :video-src="project?.videoPreviewUrl" :title="project?.videoFileName ?? project?.youtubeUrl ?? 'No video selected'" />
      <p v-if="project?.videoAsset && !project.videoPreviewUrl" class="muted">Video metadata was restored from backend storage. Upload previews are browser-only and are not restored after refresh.</p>
      <button type="button" class="extract-button" :disabled="!project?.videoAsset || isExtracting" @click="extractFrames">
        {{ isExtracting ? 'Extracting…' : 'Extract Frames' }}
      </button>
      <p v-if="!project?.videoAsset" class="muted">Upload or import a video before extracting frames.</p>
    </div>
    <div class="card">
      <h2>Projected court</h2>
      <Court2DView :projected-tracks="project?.projectedTracks" />
    </div>
  </section>

  <section class="card">
    <h2>Pipeline status</h2>
    <div class="stats-grid">
      <span><strong>{{ project?.frames.length ?? 0 }}</strong> extracted frames</span>
      <span><strong>{{ hasCalibration ? 'Saved' : 'Missing' }}</strong> calibration</span>
      <span><strong>{{ hasTracking ? 'Saved' : 'Missing' }}</strong> tracking</span>
      <span><strong>{{ hasProjectedTracks ? project?.projectedTracks.length : 0 }}</strong> projected tracks</span>
      <span><strong>{{ aliasCount }}</strong> player aliases</span>
    </div>
  </section>


  <section class="card">
    <h2>Player Alias summary</h2>
    <div class="stats-grid">
      <span><strong>{{ aliasCount }}</strong> aliases</span>
      <span><strong>{{ aliasedTrackCount }}</strong> aliased tracks</span>
      <span><strong>{{ unaliasedTrackCount }}</strong> unaliased tracks</span>
    </div>
    <p class="muted">Aliases are manual, local, project-scoped mappings for future Player Value work; raw tracking is not modified.</p>
    <RouterLink v-if="hasTracking" class="button small" :to="`/projects/${projectId}/tracking-review`">Assign aliases in Tracking Review</RouterLink>
  </section>

  <section class="card">
    <h2>Extracted frames</h2>
    <p v-if="!project?.frames.length" class="muted">No extracted frames yet. Click Extract Frames after uploading an MP4.</p>
    <div v-else class="frame-strip">
      <article v-for="frame in project.frames" :key="frame.frame_id" class="frame-card">
        <img :src="apiClient.frameImageUrl(projectId, frame.frame_index)" :alt="`Frame ${frame.frame_index}`" />
        <strong>Frame {{ frame.frame_index }}</strong>
        <span>{{ frame.timestamp_seconds.toFixed(2) }}s</span>
        <RouterLink class="button small" :to="`/projects/${projectId}/calibration?frameIndex=${frame.frame_index}`">Use for calibration</RouterLink>
        <RouterLink class="button small secondary-link" :to="`/projects/${projectId}/quiz-builder?frameIndex=${frame.frame_index}`">Build Quiz</RouterLink>
      </article>
    </div>
  </section>


  <section class="card">
    <h2>Decision Quiz Prompts</h2>
    <div v-if="quizErrorMessage" class="error-card" role="alert">
      <strong>{{ quizErrorCode }}</strong>
      <p>{{ quizErrorMessage }}</p>
      <small v-if="quizErrorHint">{{ quizErrorHint }}</small>
    </div>
    <p v-else-if="isLoadingQuizPrompts" class="muted">Loading quiz prompts…</p>
    <p v-else-if="!quizPrompts.length" class="muted">No quiz prompts yet. Use Build Quiz on an extracted frame.</p>
    <div v-else class="quiz-list">
      <article v-for="prompt in quizPrompts" :key="prompt.prompt_id" class="quiz-card">
        <strong>{{ prompt.question }}</strong>
        <span class="difficulty-badge" :class="`difficulty-${promptDifficulty(prompt).toLowerCase().replace(/_/g, '-')}`">{{ promptDifficultyLabel(prompt) }}</span>
        <span>Frame {{ prompt.frame_index }} · {{ prompt.options.length }} options · {{ hasPromptExpectedValues(prompt) ? 'Expected values entered' : 'Expected values missing' }}</span>
        <RouterLink class="button small" :to="`/projects/${projectId}/quiz/${prompt.prompt_id}`">Play</RouterLink>
      </article>
    </div>
  </section>

</template>

<style scoped>

.sample-badge {
  background: #dbeafe;
  border: 1px solid #60a5fa;
  border-radius: 999px;
  color: #1d4ed8;
  display: inline-flex;
  font-size: 0.75rem;
  font-weight: 800;
  margin-left: 0.5rem;
  padding: 0.2rem 0.55rem;
  text-transform: uppercase;
}

.source-governance-card {
  display: grid;
  gap: 1rem;
}

.section-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.warning-badge {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 999px;
  color: #92400e;
  font-weight: 800;
  padding: 0.25rem 0.65rem;
}

.source-form {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.source-form label {
  display: grid;
  gap: 0.35rem;
  font-weight: 700;
}

.source-form select,
.source-form textarea {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 0.6rem;
}

.checkbox-label {
  align-items: center;
  display: flex !important;
  gap: 0.5rem !important;
}

.full-width {
  grid-column: 1 / -1;
}

.error-text {
  color: #b91c1c;
  font-weight: 700;
  grid-column: 1 / -1;
}

.success-message {
  color: #166534;
  font-weight: 700;
  grid-column: 1 / -1;
}
.secondary {
  background: #475569;
  margin-left: 0.75rem;
}

.extract-button {
  margin-top: 1rem;
}

.frame-strip {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.frame-card {
  border: 1px solid #dde3ee;
  border-radius: 12px;
  display: grid;
  flex: 0 0 180px;
  gap: 0.35rem;
  padding: 0.75rem;
}

.frame-card img {
  aspect-ratio: 16 / 9;
  background: #111827;
  border-radius: 8px;
  object-fit: cover;
  width: 100%;
}

.small {
  font-size: 0.85rem;
  padding: 0.5rem 0.65rem;
  text-align: center;
}

.secondary-link {
  background: #475569;
}

.quiz-list {
  display: grid;
  gap: 0.75rem;
}

.quiz-card {
  align-items: center;
  border: 1px solid #dde3ee;
  border-radius: 12px;
  display: grid;
  gap: 0.5rem;
  grid-template-columns: 1fr auto auto;
  padding: 0.75rem;
}

.metadata-list {
  display: grid;
  gap: 0.4rem;
  margin: 0 0 1rem;
}

.metadata-list div {
  display: grid;
  grid-template-columns: 90px 1fr;
}

.metadata-list dt {
  color: #475569;
  font-weight: 700;
}

.metadata-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.stats-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.stats-grid span {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 0.75rem;
}

.muted {
  color: #64748b;
}
.difficulty-badge {
  align-self: flex-start;
  border-radius: 999px;
  display: inline-flex;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  padding: 0.2rem 0.55rem;
  text-transform: uppercase;
}

.difficulty-too-easy {
  background: #dbeafe;
  color: #1d4ed8;
}

.difficulty-balanced {
  background: #dcfce7;
  color: #166534;
}

.difficulty-too-hard {
  background: #fee2e2;
  color: #b91c1c;
}

.difficulty-insufficient-data,
.difficulty-not-built {
  background: #f3f4f6;
  color: #4b5563;
}

</style>
