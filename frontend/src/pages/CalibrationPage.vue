<script setup lang="ts">
import { ref } from 'vue'
import CalibrationOverlay from '../components/CalibrationOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'

const props = defineProps<{
  projectId: string
}>()

const keypoints = ref([
  { id: 'left-corner', label: 'LC', x: 9, y: 84 },
  { id: 'right-corner', label: 'RC', x: 91, y: 84 },
  { id: 'center', label: 'C', x: 50, y: 50 },
  { id: 'rim', label: 'Rim', x: 50, y: 22 }
])
</script>

<template>
  <section class="card">
    <h1>Calibration</h1>
    <p>Project {{ props.projectId }}: manually mark court keypoints, then submit them to the backend homography stub.</p>
  </section>

  <section class="card calibration-stage">
    <VideoPlayer title="Calibration frame" />
    <CalibrationOverlay :keypoints="keypoints" />
  </section>
</template>

<style scoped>
.calibration-stage {
  position: relative;
}
</style>
