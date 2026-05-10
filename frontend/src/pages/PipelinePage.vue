<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

type PipelineStatus = 'NOT_STARTED' | 'READY' | 'DONE' | 'ERROR'
type PipelineAction =
  | { kind: 'link'; label: string; to: string }
  | { kind: 'button'; label: string; disabled?: boolean; onClick: () => void }
  | { kind: 'none'; label: string; disabledReason: string }

interface PipelineStep {
  number: number
  title: string
  status: PipelineStatus
  explanation: string
  action: PipelineAction
  disabledReason?: string
  warning?: string
}

const projectStore = useProjectStore()
const { ensureProjectHydrated, isHydrating, hydrationError, hydrationErrorCode, hydrationErrorHint } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const project = computed(() => projectStore.getProject(props.projectId))
const isExtracting = ref(false)
const actionErrorMessage = ref('')
const actionErrorCode = ref('')
const actionErrorHint = ref('')

const hasProject = computed(() => !!project.value)
const hasVideoAsset = computed(() => !!project.value?.videoAsset)
const hasFrames = computed(() => (project.value?.frames.length ?? 0) > 0)
const firstFrame = computed(() => project.value?.frames[0] ?? null)
const hasCalibration = computed(() => !!project.value?.calibration)
const hasTracking = computed(() => !!project.value && (project.value.detections.length > 0 || project.value.tracks.length > 0 || project.value.projectedTracks.length > 0))
const hasProjectedTracks = computed(() => (project.value?.projectedTracks.length ?? 0) > 0)
const calibrationFrameSelected = computed(() => !!project.value?.calibration?.frame_id)
const calibrationLink = computed(() => {
  const frameIndex = firstFrame.value?.frame_index
  return frameIndex === undefined ? `/projects/${props.projectId}/calibration` : `/projects/${props.projectId}/calibration?frameIndex=${frameIndex}`
})
const quizBuilderLink = computed(() => {
  const frameIndex = firstFrame.value?.frame_index
  return frameIndex === undefined ? `/projects/${props.projectId}/quiz-builder` : `/projects/${props.projectId}/quiz-builder?frameIndex=${frameIndex}`
})

const steps = computed<PipelineStep[]>(() => [
  {
    number: 1,
    title: 'Project Created',
    status: statusFor(hasProject.value),
    explanation: hasProject.value ? 'The backend project record is hydrated in the browser.' : 'Load or create a project before starting the MVP pipeline.',
    action: hasProject.value
      ? { kind: 'link', label: 'Open project', to: `/projects/${props.projectId}` }
      : { kind: 'link', label: 'Create project', to: '/' }
  },
  {
    number: 2,
    title: 'Video Uploaded',
    status: statusFor(hasVideoAsset.value, hasProject.value),
    explanation: hasVideoAsset.value ? describeVideo.value : 'A video asset is required before frames can be extracted.',
    action: hasVideoAsset.value
      ? { kind: 'link', label: 'Review video', to: `/projects/${props.projectId}` }
      : hasProject.value
        ? { kind: 'link', label: 'Upload from home', to: '/' }
        : blockedAction('Project metadata is still loading or unavailable.')
  },
  {
    number: 3,
    title: 'Frames Extracted',
    status: actionErrorCode.value ? 'ERROR' : statusFor(hasFrames.value, hasVideoAsset.value),
    explanation: hasFrames.value ? `${project.value?.frames.length ?? 0} frame(s) are available for calibration and quiz work.` : 'Extract sampled frame images from the uploaded MP4.',
    action: hasFrames.value
      ? { kind: 'link', label: 'Review frames', to: `/projects/${props.projectId}` }
      : hasVideoAsset.value
        ? { kind: 'button', label: isExtracting.value ? 'Extracting…' : 'Extract frames', disabled: isExtracting.value || isHydrating.value, onClick: extractFrames }
        : blockedAction('Upload or import a video before extracting frames.'),
    disabledReason: hasVideoAsset.value ? undefined : 'Video asset is missing.'
  },
  {
    number: 4,
    title: 'Calibration Frame Selected',
    status: statusFor(calibrationFrameSelected.value, hasFrames.value),
    explanation: calibrationFrameSelected.value
      ? `Calibration is tied to frame ${project.value?.calibration?.frame_id}.`
      : 'Choose an extracted frame to mark court keypoints in image pixel coordinates.',
    action: hasFrames.value
      ? { kind: 'link', label: 'Select frame', to: calibrationLink.value }
      : blockedAction('Extract frames before choosing a calibration frame.'),
    disabledReason: hasFrames.value ? undefined : 'No extracted frames are available.'
  },
  {
    number: 5,
    title: 'Calibration Saved',
    status: statusFor(hasCalibration.value, hasFrames.value),
    explanation: hasCalibration.value
      ? `${project.value?.calibrationPairs.length ?? 0} keypoint pair(s) and homography data are saved.`
      : 'Save 4+ image/court keypoint pairs so image tracks can be projected to court feet.',
    action: hasFrames.value
      ? { kind: 'link', label: hasCalibration.value ? 'Edit calibration' : 'Mark keypoints', to: calibrationLink.value }
      : blockedAction('Extract frames before saving calibration.'),
    disabledReason: hasFrames.value ? undefined : 'Calibration requires at least one extracted frame.'
  },
  {
    number: 6,
    title: 'Tracking Run',
    status: statusFor(hasTracking.value, hasFrames.value),
    explanation: hasTracking.value ? 'Detections/tracks are present in hydrated state.' : 'Run backend detection/tracking on extracted frames.',
    action: hasFrames.value
      ? { kind: 'link', label: hasTracking.value ? 'View raw tracking' : 'Run tracking', to: `/projects/${props.projectId}/tracking` }
      : blockedAction('Extract frames before running tracking.'),
    disabledReason: hasFrames.value ? undefined : 'Tracking needs extracted frames.',
    warning: hasFrames.value && !hasCalibration.value ? 'Tracking can run without calibration, but 2D projection may not be meaningful until calibration is saved.' : undefined
  },
  {
    number: 7,
    title: 'Tracking Quality Review',
    status: statusFor(false, hasTracking.value),
    explanation: hasTracking.value
      ? 'Inspect raw detections and save cleaned tracking artifacts before trusting projected paths.'
      : 'Run tracking before excluding false-positive detections or full tracks.',
    action: hasTracking.value
      ? { kind: 'link', label: 'Open QC review', to: `/projects/${props.projectId}/tracking-review` }
      : blockedAction('Run tracking before quality review.'),
    disabledReason: hasTracking.value ? undefined : 'No raw tracking artifact exists yet.'
  },
  {
    number: 8,
    title: '2D Court Projection Available',
    status: statusFor(hasProjectedTracks.value, hasTracking.value && hasCalibration.value),
    explanation: hasProjectedTracks.value
      ? `${project.value?.projectedTracks.length ?? 0} projected track(s) are ready for Court2DView.`
      : 'Projected tracks are only considered done when backend court-feet points exist.',
    action: hasProjectedTracks.value
      ? { kind: 'link', label: 'View court projection', to: `/projects/${props.projectId}/tracking` }
      : hasTracking.value && !hasCalibration.value
        ? blockedAction('Save calibration and rerun tracking to create meaningful court projection points.')
        : hasTracking.value
          ? { kind: 'link', label: 'Rerun tracking', to: `/projects/${props.projectId}/tracking` }
          : blockedAction('Run tracking after calibration to produce projected court paths.'),
    disabledReason: hasProjectedTracks.value ? undefined : 'No projectedTracks artifact exists yet.'
  },
  {
    number: 9,
    title: 'Decision Quiz Ready',
    status: 'NOT_STARTED',
    explanation: 'Future MVP step: build and play decision prompts from extracted frames and normalized arrows.',
    action: hasFrames.value
      ? { kind: 'link', label: 'Build quiz prompt', to: quizBuilderLink.value }
      : blockedAction('Extract frames before building quiz prompts.'),
    disabledReason: hasFrames.value ? 'Future step; quiz tooling is available for early prompt drafting.' : 'No extracted frames are available.'
  }
])

const describeVideo = computed(() => {
  const video = project.value?.videoAsset
  if (!video) return 'No video asset is saved yet.'
  const filename = video.filename ? ` (${video.filename})` : ''
  return `Video asset ${video.asset_id}${filename} is hydrated from backend metadata.`
})

onMounted(() => {
  void ensureProjectHydrated(props.projectId, { force: true }).catch(() => undefined)
})

function statusFor(done: boolean, ready = true): PipelineStatus {
  if (done) return 'DONE'
  return ready ? 'READY' : 'NOT_STARTED'
}

function blockedAction(disabledReason: string): PipelineAction {
  return { kind: 'none', label: 'Blocked', disabledReason }
}

function showActionError(error: unknown) {
  if (isApiClientError(error)) {
    actionErrorCode.value = error.code
    actionErrorMessage.value = error.message
    actionErrorHint.value = error.debug_hint ?? ''
  } else {
    actionErrorCode.value = 'PIPELINE_ACTION_ERROR'
    actionErrorMessage.value = 'Could not complete the pipeline action.'
    actionErrorHint.value = error instanceof Error ? error.message : ''
  }
}

async function extractFrames() {
  const videoAsset = project.value?.videoAsset
  if (!videoAsset || isExtracting.value) return
  isExtracting.value = true
  actionErrorMessage.value = ''
  actionErrorCode.value = ''
  actionErrorHint.value = ''

  try {
    const response = await apiClient.extractFrames(props.projectId, {
      project_id: props.projectId,
      video_asset_id: videoAsset.asset_id,
      target_fps: 1,
      max_frames: 120
    })
    projectStore.setFrames(props.projectId, response.frames)
  } catch (error) {
    showActionError(error)
  } finally {
    isExtracting.value = false
  }
}
</script>

<template>
  <section class="card pipeline-hero">
    <div>
      <p class="eyebrow">MVP Pipeline</p>
      <h1>{{ project?.name ?? 'Project pipeline' }}</h1>
      <p>Follow each hydrated artifact from project creation through court projection. Statuses only turn DONE when saved state exists.</p>
    </div>
    <RouterLink class="button secondary" :to="`/projects/${projectId}`">Back to project</RouterLink>
  </section>

  <section v-if="isHydrating" class="card" aria-live="polite">
    <strong>Loading project…</strong>
    <p>Hydrating project, video, frames, calibration, tracking, and projection artifacts from backend storage.</p>
  </section>

  <section v-if="hydrationError" class="error-card" role="alert">
    <strong>{{ hydrationErrorCode }}</strong>
    <p>{{ hydrationError }}</p>
    <small v-if="hydrationErrorHint">{{ hydrationErrorHint }}</small>
  </section>

  <section v-if="actionErrorMessage" class="error-card" role="alert">
    <strong>{{ actionErrorCode }}</strong>
    <p>{{ actionErrorMessage }}</p>
    <small v-if="actionErrorHint">{{ actionErrorHint }}</small>
  </section>

  <section class="pipeline-list" aria-label="Pipeline steps">
    <article v-for="step in steps" :key="step.number" class="card pipeline-step" :class="`status-${step.status.toLowerCase()}`">
      <div class="step-index">{{ step.number }}</div>
      <div class="step-body">
        <div class="step-title-row">
          <h2>{{ step.title }}</h2>
          <span class="status-pill">{{ step.status }}</span>
        </div>
        <p>{{ step.explanation }}</p>
        <p v-if="step.warning" class="warning">{{ step.warning }}</p>
        <p v-if="step.disabledReason" class="muted">Blocked: {{ step.disabledReason }}</p>
      </div>
      <div class="step-action">
        <RouterLink v-if="step.action.kind === 'link'" class="button" :to="step.action.to">{{ step.action.label }}</RouterLink>
        <button v-else-if="step.action.kind === 'button'" type="button" :disabled="step.action.disabled" @click="step.action.onClick">
          {{ step.action.label }}
        </button>
        <button v-else type="button" disabled :title="step.action.disabledReason">{{ step.action.label }}</button>
        <small v-if="step.action.kind === 'none'">{{ step.action.disabledReason }}</small>
      </div>
    </article>
  </section>
</template>

<style scoped>
.pipeline-hero {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.eyebrow {
  color: #1f6feb;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin: 0 0 0.25rem;
  text-transform: uppercase;
}

.pipeline-list {
  display: grid;
  gap: 1rem;
}

.pipeline-step {
  align-items: flex-start;
  display: grid;
  gap: 1rem;
  grid-template-columns: auto minmax(0, 1fr) auto;
  margin-bottom: 0;
}

.step-index {
  align-items: center;
  background: #e2e8f0;
  border-radius: 999px;
  display: inline-flex;
  font-weight: 800;
  height: 2.25rem;
  justify-content: center;
  width: 2.25rem;
}

.step-title-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.step-title-row h2 {
  margin: 0;
}

.status-pill {
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.3rem 0.55rem;
}

.status-done .status-pill {
  background: #dcfce7;
  color: #166534;
}

.status-ready .status-pill {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-not_started .status-pill {
  background: #f1f5f9;
  color: #475569;
}

.status-error .status-pill {
  background: #fee2e2;
  color: #991b1b;
}

.step-action {
  display: grid;
  gap: 0.35rem;
  justify-items: end;
  min-width: 9rem;
}

.step-action small,
.muted {
  color: #64748b;
}

.warning {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  color: #9a3412;
  padding: 0.65rem;
}

.secondary {
  background: #475569;
}

@media (max-width: 720px) {
  .pipeline-hero,
  .pipeline-step {
    display: block;
  }

  .step-action {
    justify-items: start;
    margin-top: 1rem;
  }
}
</style>
