<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { apiClient, isApiClientError, type CourtKeypointPair } from '../api/client'
import CalibrationOverlay from '../components/CalibrationOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)

const project = computed(() => projectStore.getProject(props.projectId))
const frameIndex = computed(() => {
  const raw = route.query.frameIndex
  const value = Array.isArray(raw) ? raw[0] : raw
  const parsed = value === undefined ? Number.NaN : Number(value)
  return Number.isFinite(parsed) ? parsed : null
})
const selectedFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === frameIndex.value) ?? null)
const frameSrc = computed(() => (frameIndex.value !== null ? apiClient.frameImageUrl(props.projectId, frameIndex.value) : undefined))
const imageNaturalWidth = ref(selectedFrame.value?.width ?? 100)
const imageNaturalHeight = ref(selectedFrame.value?.height ?? 100)
const displayWidth = ref(0)
const displayHeight = ref(0)
const isSaving = ref(false)
const savedCalibrationId = ref('')
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')

interface CourtKeypointOption {
  id: string
  label: string
  help: string
  courtPoint: { x: number; y: number; label: string }
}

const keypoints: CourtKeypointOption[] = [
  { id: 'near_left_corner', label: 'Near left corner', help: 'Pick the near sideline/baseline corner.', courtPoint: { x: 0, y: 50, label: 'near left corner' } },
  { id: 'near_right_corner', label: 'Near right corner', help: 'Pick the opposite near baseline corner.', courtPoint: { x: 94, y: 50, label: 'near right corner' } },
  { id: 'far_left_corner', label: 'Far left corner', help: 'Pick the far sideline/baseline corner.', courtPoint: { x: 0, y: 0, label: 'far left corner' } },
  { id: 'far_right_corner', label: 'Far right corner', help: 'Pick the opposite far baseline corner.', courtPoint: { x: 94, y: 0, label: 'far right corner' } },
  { id: 'left_free_throw', label: 'Left free throw line', help: 'Pick the middle of the left free throw line.', courtPoint: { x: 19, y: 25, label: 'left free throw line' } },
  { id: 'right_free_throw', label: 'Right free throw line', help: 'Pick the middle of the right free throw line.', courtPoint: { x: 75, y: 25, label: 'right free throw line' } },
  { id: 'left_rim_center', label: 'Left rim center', help: 'Pick the visible center of the left rim.', courtPoint: { x: 5.25, y: 25, label: 'left rim center' } },
  { id: 'right_rim_center', label: 'Right rim center', help: 'Pick the visible center of the right rim.', courtPoint: { x: 88.75, y: 25, label: 'right rim center' } }
]
const activeKeypointId = ref(keypoints[0].id)
const status = ref('Choose an extracted frame, then click the first requested keypoint on the image.')

const pairs = computed(() => project.value?.calibrationPairs ?? [])
const nextUnmarked = computed(() => keypoints.find((keypoint) => !pairs.value.some((pair) => pair.keypoint_id === keypoint.id)))
const reprojectionError = computed(() => project.value?.calibration?.reprojection_error)
const canSave = computed(() => pairs.value.length >= 4 && !!selectedFrame.value && !isSaving.value)
const canContinue = computed(() => !!project.value?.calibration?.homography && savedCalibrationId.value === props.projectId)

function selectKeypoint(keypointId: string) {
  activeKeypointId.value = keypointId
}

function onImageLoad(event: Event) {
  const image = event.target as HTMLImageElement
  imageNaturalWidth.value = image.naturalWidth || selectedFrame.value?.width || 100
  imageNaturalHeight.value = image.naturalHeight || selectedFrame.value?.height || 100
  displayWidth.value = image.clientWidth
  displayHeight.value = image.clientHeight
}

function addPoint(pair: CourtKeypointPair) {
  const nextPairs = pairs.value.filter((item) => item.keypoint_id !== pair.keypoint_id)
  nextPairs.push(pair)
  projectStore.setCalibrationPairs(props.projectId, nextPairs)
  const remaining = keypoints.find((keypoint) => !nextPairs.some((item) => item.keypoint_id === keypoint.id))
  activeKeypointId.value = remaining?.id ?? pair.keypoint_id
  savedCalibrationId.value = ''
  status.value = `Saved pixel point (${pair.image_point.x.toFixed(1)}, ${pair.image_point.y.toFixed(1)}) for ${pair.court_point.label}. ${remaining ? 'Continue with the highlighted keypoint.' : 'All keypoints are marked; save calibration when ready.'}`
}

function removePoint(keypointId: string) {
  projectStore.setCalibrationPairs(props.projectId, pairs.value.filter((pair) => pair.keypoint_id !== keypointId))
  activeKeypointId.value = keypointId
  savedCalibrationId.value = ''
  status.value = 'Marker removed. Click the frame to place it again.'
}

function showError(error: unknown) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'CALIBRATION_SAVE_ERROR'
    errorMessage.value = 'Could not save calibration.'
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

async function saveBackendCalibration() {
  if (!selectedFrame.value || isSaving.value) return
  isSaving.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const response = await apiClient.saveCalibration(props.projectId, {
      project_id: props.projectId,
      frame_id: selectedFrame.value.frame_id,
      keypoint_pairs: pairs.value,
      homography: null,
      debug_metadata: { source: 'frontend_manual_calibration' }
    })
    projectStore.setCalibration(props.projectId, response.calibration)
    savedCalibrationId.value = props.projectId
    status.value = `Backend calibration saved with ${response.calibration.keypoint_pairs.length} point(s).`
  } catch (error) {
    showError(error)
  } finally {
    isSaving.value = false
  }
}

function continueToTracking() {
  if (!canContinue.value) return
  router.push(`/projects/${props.projectId}/tracking`)
}
</script>

<template>
  <section class="card">
    <h1>Calibration</h1>
    <p>Project {{ props.projectId }}: manually mark image points for known court keypoints. MVP does not run automatic court detection.</p>
    <p v-if="selectedFrame">Selected frame {{ selectedFrame.frame_index }} at {{ selectedFrame.timestamp_seconds.toFixed(2) }}s.</p>
    <p v-else-if="frameIndex !== null" class="warning">Frame {{ frameIndex }} is not in the local project store. Return to the project page after extracting frames, then choose a calibration frame.</p>
    <p v-else class="warning">Choose an extracted frame from the project page for pixel-accurate calibration.</p>
    <p class="status">{{ status }}</p>
    <p v-if="reprojectionError !== null && reprojectionError !== undefined" class="status">Reprojection error: {{ reprojectionError.toFixed(3) }}</p>
    <button type="button" :disabled="!canSave" @click="saveBackendCalibration">{{ isSaving ? 'Saving…' : 'Save backend calibration' }}</button>
    <button type="button" class="secondary" :disabled="!canContinue" @click="continueToTracking">Continue to tracking</button>
    <RouterLink class="button secondary" :to="`/projects/${projectId}`">Back to project</RouterLink>
  </section>

  <section v-if="errorMessage" class="error-card" role="alert">
    <strong>{{ errorCode }}</strong>
    <p>{{ errorMessage }}</p>
    <small v-if="errorHint">{{ errorHint }}</small>
  </section>

  <section class="card calibration-stage">
    <div v-if="frameSrc" class="calibration-frame-shell">
      <img :src="frameSrc" alt="Calibration frame" @load="onImageLoad" />
      <CalibrationOverlay
        :keypoints="keypoints"
        :pairs="pairs"
        :active-keypoint-id="activeKeypointId"
        :image-natural-width="imageNaturalWidth"
        :image-natural-height="imageNaturalHeight"
        :display-width="displayWidth"
        :display-height="displayHeight"
        @add-point="addPoint"
        @select-keypoint="selectKeypoint"
        @remove-point="removePoint"
      />
    </div>
    <VideoPlayer v-else :video-src="project?.videoPreviewUrl" title="Calibration frame" />
  </section>
</template>

<style scoped>
.calibration-stage {
  position: relative;
}

.calibration-frame-shell {
  background: #111827;
  border-radius: 16px;
  margin: 0 auto;
  max-width: 100%;
  overflow: hidden;
  position: relative;
}

.calibration-frame-shell img {
  display: block;
  height: auto;
  width: 100%;
}

.status {
  color: #475569;
  font-weight: 700;
}

.warning {
  color: #b45309;
  font-weight: 700;
}

.secondary {
  background: #475569;
  margin-left: 0.75rem;
}
</style>
