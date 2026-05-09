<script setup lang="ts">
interface TrackPoint {
  id: string
  label: string
  x: number
  y: number
}

defineProps<{
  tracks: TrackPoint[]
}>()
</script>

<template>
  <svg class="track-overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Tracking overlay">
    <g v-for="track in tracks" :key="track.id">
      <rect :x="track.x - 4" :y="track.y - 8" width="8" height="14" rx="1" />
      <text :x="track.x - 4" :y="track.y - 10">{{ track.label }}</text>
    </g>
  </svg>
</template>

<style scoped>
.track-overlay {
  inset: 0;
  pointer-events: none;
  position: absolute;
}

rect {
  fill: rgb(34 197 94 / 0.18);
  stroke: #22c55e;
  stroke-width: 0.6;
}

text {
  fill: white;
  font-size: 4px;
  paint-order: stroke;
  stroke: #0f172a;
  stroke-width: 0.5px;
}
</style>
