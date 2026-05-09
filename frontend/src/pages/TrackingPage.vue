<script setup lang="ts">
import { computed, ref } from 'vue'
import { apiClient, isApiClientError, type Detection, type PlayerTrack, type ProjectedPlayerTrack, type RunTrackingResponse } from '../api/client'
import Court2DView from '../components/Court2DView.vue'
import TrackOverlay from '../components/TrackOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)
const project = computed(() => projectStore.getProject(props.projectId))
const isRunning = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')
const pipelineOutput = ref<RunTrackingResponse['pipeline_output'] | null>(null)
const debugMetadata = ref<RunTrackingResponse['debug_metadata'] | null>(null)

const demoDetections: Detection[] = [
  { detection_id: 'det-1', frame_id: 'demo-frame', frame_index: 0, box: { x: 31, y: 42, width: 8, height: 18 }, confidence: 0.92, class_name: 'person', track_id: 'track-1', metadata: {} },
  { detection_id: 'det-2', frame_id: 'demo-frame', frame_index: 0, box: { x: 48, y: 37, width: 7, height: 17 }, confidence: 0.88, class_name: 'person', track_id: 'track-2', metadata: {} },
  { detection_id: 'det-3', frame_id: 'demo-frame', frame_index: 0, box: { x: 62, y: 45, width: 8, height: 19 }, confidence: 0.81, class_name: 'person', track_id: 'track-3', metadata: {} }
]

const demoTracks: PlayerTrack[] = [
  { track_id: 'track-1', player_id: '#1', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, image_point_x: 35, image_point_y: 60 }], metadata: {} },
  { track_id: 'track-2', player_id: '#2', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, image_point_x: 51.5, image_point_y: 54 }], metadata: {} },
  { track_id: 'track-3', player_id: '#3', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, image_point_x: 66, image_point_y: 64 }], metadata: {} }
]

const demoProjectedTracks: ProjectedPlayerTrack[] = [
  { track_id: 'track-1', player_id: '#1', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, court_x: 30, court_y: 26, metadata: {} }], metadata: {} },
  { track_id: 'track-2', player_id: '#2', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, court_x: 45, court_y: 20, metadata: {} }], metadata: {} },
  { track_id: 'track-3', player_id: '#3', points: [{ frame_id: 'demo-frame', frame_index: 0, timestamp_seconds: 0, court_x: 60, court_y: 31, metadata: {} }], metadata: {} }
]

const hasBackendResult = computed(() => !!project.value && (project.value.detections.length > 0 || project.value.tracks.length > 0 || project.value.projectedTracks.length > 0))
const detections = computed(() => (hasBackendResult.value ? project.value?.detections ?? [] : demoDetections))
const tracks = computed(() => (hasBackendResult.value ? project.value?.tracks ?? [] : demoTracks))
const projectedTracks = computed(() => (hasBackendResult.value ? project.value?.projectedTracks ?? [] : demoProjectedTracks))
const currentFrameIndex = computed(() => detections.value[0]?.frame_index ?? project.value?.frames[0]?.frame_index ?? 0)
const currentFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === currentFrameIndex.value) ?? project.value?.frames[0] ?? null)
const frameSrc = computed(() => (currentFrame.value ? apiClient.frameImageUrl(props.projectId, currentFrame.value.frame_index) : undefined))
const overlayWidth = computed(() => (hasBackendResult.value ? currentFrame.value?.width ?? project.value?.videoAsset?.width ?? 100 : 100))
const overlayHeight = computed(() => (hasBackendResult.value ? currentFrame.value?.height ?? project.value?.videoAsset?.height ?? 100 : 100))
const detectorMode = computed(() => {
  const outputMode = pipelineOutput.value?.detector_mode
  const detector = debugMetadata.value?.detector
  if (typeof outputMode === 'string') return outputMode
  if (detector && typeof detector === 'object' && 'detector_mode' in detector && typeof detector.detector_mode === 'string') return detector.detector_mode
  if (detector && typeof detector === 'object' && 'mode' in detector && typeof detector.mode === 'string') return detector.mode
  return 'unknown'
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
  if (isRunning.value) return
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
    pipelineOutput.value = runResponse.pipeline_output ?? null
    debugMetadata.value = runResponse.debug_metadata ?? null
    const tracksResponse = await apiClient.getTracks(props.projectId)
    projectStore.setTracks(props.projectId, {
      detections: tracksResponse.tracking?.detections ?? runResponse.detections,
      tracks: tracksResponse.tracking?.tracks ?? runResponse.tracks,
      projectedTracks: tracksResponse.projected_tracks
    })
    pipelineOutput.value = tracksResponse.tracking?.pipeline_output ?? pipelineOutput.value
    debugMetadata.value = tracksResponse.tracking?.debug_metadata ?? debugMetadata.value
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
    <button type="button" :disabled="isRunning" @click="runTracking">{{ isRunning ? 'Running…' : 'Run Tracking' }}</button>
    <p v-if="!hasBackendResult" class="demo-label">Showing demo placeholder tracks until backend tracking is run.</p>
    <div class="stats-grid">
      <span><strong>{{ detections.length }}</strong> detections</span>
      <span><strong>{{ tracks.length }}</strong> tracks</span>
      <span><strong>{{ projectedTracks.length }}</strong> projected tracks</span>
      <span><strong>{{ detectorMode }}</strong> detector mode</span>
    </div>
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

.demo-label {
  color: #b45309;
  font-weight: 700;
}

.stats-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  margin-top: 1rem;
}

.stats-grid span {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 0.75rem;
}
</style>
