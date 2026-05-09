<script setup lang="ts">
import { ref } from 'vue'
import Court2DView from '../components/Court2DView.vue'
import TrackOverlay from '../components/TrackOverlay.vue'
import VideoPlayer from '../components/VideoPlayer.vue'

const props = defineProps<{
  projectId: string
}>()

const tracks = ref([
  { id: 'p1', label: '#1', x: 35, y: 58 },
  { id: 'p2', label: '#2', x: 48, y: 52 },
  { id: 'p3', label: '#3', x: 61, y: 63 }
])

const courtPlayers = ref([
  { id: 'p1', team: 'home' as const, x: 30, y: 26 },
  { id: 'p2', team: 'away' as const, x: 45, y: 20 },
  { id: 'p3', team: 'unknown' as const, x: 60, y: 31 }
])
</script>

<template>
  <section class="card">
    <h1>Tracking demo</h1>
    <p>Project {{ props.projectId }}: run detector/tracker/projector stubs and visualize demo tracks.</p>
  </section>

  <section class="grid">
    <div class="card tracking-stage">
      <VideoPlayer title="Tracking preview" />
      <TrackOverlay :tracks="tracks" />
    </div>
    <div class="card">
      <h2>2D court projection</h2>
      <Court2DView :players="courtPlayers" />
    </div>
  </section>
</template>

<style scoped>
.tracking-stage {
  position: relative;
}
</style>
