<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { Calibration, CourtKeypointPair } from '../api/client'
import CalibrationOverlay from '../components/CalibrationOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)

const project = computed(() => projectStore.getProject(props.projectId))

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
const status = ref('Click the first requested keypoint on the preview.')

const pairs = computed(() => project.value?.calibrationPairs ?? [])
const nextUnmarked = computed(() => keypoints.find((keypoint) => !pairs.value.some((pair) => pair.keypoint_id === keypoint.id)))

function selectKeypoint(keypointId: string) {
  activeKeypointId.value = keypointId
}

function addPoint(pair: CourtKeypointPair) {
  const nextPairs = pairs.value.filter((item) => item.keypoint_id !== pair.keypoint_id)
  nextPairs.push(pair)
  projectStore.setCalibrationPairs(props.projectId, nextPairs)
  activeKeypointId.value = nextUnmarked.value?.id ?? pair.keypoint_id
  status.value = `Saved image point for ${pair.court_point.label}. ${nextUnmarked.value ? 'Continue with the highlighted keypoint.' : 'All keypoints are marked; save calibration when ready.'}`
}

function removePoint(keypointId: string) {
  projectStore.setCalibrationPairs(props.projectId, pairs.value.filter((pair) => pair.keypoint_id !== keypointId))
  activeKeypointId.value = keypointId
  status.value = 'Marker removed. Click the frame to place it again.'
}

function saveLocalCalibration() {
  const calibration: Calibration = {
    project_id: props.projectId,
    frame_id: project.value?.frames[0]?.frame_id ?? null,
    keypoint_pairs: pairs.value,
    homography: null,
    reprojection_error: null,
    debug_metadata: { source: 'frontend_mvp_manual_calibration' }
  }
  projectStore.setCalibration(props.projectId, calibration)
  status.value = `Saved ${pairs.value.length} calibration point(s) in the project store.`
}
</script>

<template>
  <section class="card">
    <h1>Calibration</h1>
    <p>Project {{ props.projectId }}: manually mark image points for known court keypoints. MVP does not run automatic court detection.</p>
    <p class="status">{{ status }}</p>
    <button type="button" :disabled="pairs.length < 4" @click="saveLocalCalibration">Save calibration points</button>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Continue to tracking</RouterLink>
  </section>

  <section class="card calibration-stage">
    <VideoPlayer :video-src="project?.videoPreviewUrl" title="Calibration frame" />
    <CalibrationOverlay
      :keypoints="keypoints"
      :pairs="pairs"
      :active-keypoint-id="activeKeypointId"
      @add-point="addPoint"
      @select-keypoint="selectKeypoint"
      @remove-point="removePoint"
    />
  </section>
</template>

<style scoped>
.calibration-stage {
  position: relative;
}

.status {
  color: #475569;
  font-weight: 700;
}

.secondary {
  background: #475569;
  margin-left: 0.75rem;
}
</style>
