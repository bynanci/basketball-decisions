<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import Court2DView from '../components/Court2DView.vue'
import TrackOverlay from '../components/TrackOverlay.vue'
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
const isRunning = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')
const pipelineOutput = computed(() => project.value?.trackingPipelineOutput ?? null)
const debugMetadata = computed(() => project.value?.trackingDebugMetadata ?? null)

const hasBackendResult = computed(() => !!project.value && (project.value.detections.length > 0 || project.value.tracks.length > 0 || project.value.projectedTracks.length > 0))
const detections = computed(() => project.value?.detections ?? [])
const tracks = computed(() => project.value?.tracks ?? [])
const projectedTracks = computed(() => project.value?.projectedTracks ?? [])
const isCalibrationMissing = computed(() => !project.value?.calibration)
const currentFrameIndex = computed(() => detections.value[0]?.frame_index ?? project.value?.frames[0]?.frame_index ?? 0)
const currentFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === currentFrameIndex.value) ?? project.value?.frames[0] ?? null)
const frameSrc = computed(() => (currentFrame.value ? apiClient.frameImageUrl(props.projectId, currentFrame.value.frame_index) : undefined))
const overlayWidth = computed(() => currentFrame.value?.width ?? project.value?.videoAsset?.width ?? 100)
const overlayHeight = computed(() => currentFrame.value?.height ?? project.value?.videoAsset?.height ?? 100)
const detectorMode = computed(() => {
  const outputMode = pipelineOutput.value?.detector_mode
  const detector = debugMetadata.value?.detector
  if (typeof outputMode === 'string') return outputMode
  if (detector && typeof detector === 'object' && 'detector_mode' in detector && typeof detector.detector_mode === 'string') return detector.detector_mode
  if (detector && typeof detector === 'object' && 'mode' in detector && typeof detector.mode === 'string') return detector.mode
  return 'unknown'
})

onMounted(() => {
  void ensureProjectHydrated(props.projectId, { force: true }).catch(() => undefined)
})

function showError(error: unknown) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'TRACKING_ERROR'
    errorMessage.value = 'Could not run tracking.'
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

async function runTracking() {
  if (isRunning.value || isHydrating.value) return
  isRunning.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const runResponse = await apiClient.runTracking(props.projectId, {
      project_id: props.projectId,
      confidence_threshold: 0.25,
      iou_threshold: 0.3,
      max_players: 10
    })
    const tracksResponse = await apiClient.getTracks(props.projectId)
    projectStore.setTracks(props.projectId, {
      detections: tracksResponse.tracking?.detections ?? runResponse.detections,
      tracks: tracksResponse.tracking?.tracks ?? runResponse.tracks,
      projectedTracks: tracksResponse.projected_tracks,
      pipelineOutput: tracksResponse.tracking?.pipeline_output ?? runResponse.pipeline_output ?? null,
      debugMetadata: tracksResponse.tracking?.debug_metadata ?? runResponse.debug_metadata ?? null
    })
  } catch (error) {
    showError(error)
  } finally {
    isRunning.value = false
  }
}
</script>

<template>
  <section class="card">
    <h1>Tracking</h1>
    <p>Project {{ props.projectId }}: run backend detection/tracking, then visualize image-space tracks and projected 2D court paths.</p>
    <button type="button" :disabled="isRunning || isHydrating" @click="runTracking">{{ isRunning ? 'Running…' : 'Run Tracking' }}</button>
    <RouterLink v-if="hasBackendResult" class="button secondary review-link" :to="`/projects/${projectId}/tracking-review`">Open Tracking Review</RouterLink>
    <p v-if="isCalibrationMissing" class="warning">Tracking can run, but 2D projection needs calibration for meaningful court coordinates.</p>
    <p v-if="!hasBackendResult" class="empty-label">No backend tracking results yet. Click Run Tracking to request detections, tracks, and projected court paths.</p>
    <div class="stats-grid">
      <span><strong>{{ detections.length }}</strong> detections</span>
      <span><strong>{{ tracks.length }}</strong> tracks</span>
      <span><strong>{{ projectedTracks.length }}</strong> projected tracks</span>
      <span><strong>{{ detectorMode }}</strong> detector mode</span>
    </div>
  </section>

  <section v-if="isHydrating" class="card" aria-live="polite">
    <strong>Loading project…</strong>
    <p>Recovering frames, tracking output, and projected tracks from backend storage.</p>
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

  <section class="grid">
    <div class="card tracking-stage">
      <div v-if="frameSrc" class="tracking-frame-shell">
        <img :src="frameSrc" :alt="`Tracking frame ${currentFrameIndex}`" />
        <TrackOverlay :detections="detections" :tracks="tracks" :frame-index="currentFrameIndex" :width="overlayWidth" :height="overlayHeight" />
      </div>
      <template v-else>
        <VideoPlayer :video-src="project?.videoPreviewUrl" title="Tracking preview" />
        <TrackOverlay :detections="detections" :tracks="tracks" :frame-index="0" />
      </template>
    </div>
    <div class="card">
      <h2>2D court projection</h2>
      <Court2DView :projected-tracks="projectedTracks" />
    </div>
  </section>
</template>

<style scoped>
.tracking-stage {
  position: relative;
}

.tracking-frame-shell {
  background: #111827;
  border-radius: 16px;
  overflow: hidden;
  position: relative;
}

.tracking-frame-shell img {
  display: block;
  width: 100%;
}

.empty-label,
.warning {
  color: #b45309;
  font-weight: 700;
}

.stats-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  margin-top: 1rem;
}

.review-link {
  margin-left: 0.75rem;
}

.secondary {
  background: #475569;
}

.stats-grid span {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 0.75rem;
}
</style>
