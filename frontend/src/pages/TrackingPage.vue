<script setup lang="ts">
import { computed } from 'vue'
import Court2DView from '../components/Court2DView.vue'
import TrackOverlay from '../components/TrackOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'
import type { Detection, PlayerTrack, ProjectedPlayerTrack } from '../api/client'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)
const project = computed(() => projectStore.getProject(props.projectId))

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

const detections = computed(() => (project.value?.detections.length ? project.value.detections : demoDetections))
const tracks = computed(() => (project.value?.tracks.length ? project.value.tracks : demoTracks))
const projectedTracks = computed(() => (project.value?.projectedTracks.length ? project.value.projectedTracks : demoProjectedTracks))
</script>

<template>
  <section class="card">
    <h1>Tracking demo</h1>
    <p>Project {{ props.projectId }}: visualize player boxes, track ids, image-space paths, and projected 2D court paths.</p>
  </section>

  <section class="grid">
    <div class="card tracking-stage">
      <VideoPlayer :video-src="project?.videoPreviewUrl" title="Tracking preview" />
      <TrackOverlay :detections="detections" :tracks="tracks" :frame-index="0" />
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
</style>
