<script setup lang="ts">
import type { Detection, PlayerTrack } from '../api/client'

const props = withDefaults(
  defineProps<{
    detections?: Detection[]
    tracks?: PlayerTrack[]
    frameIndex?: number
    width?: number
    height?: number
  }>(),
  { width: 100, height: 100 }
)

function pathForTrack(track: PlayerTrack) {
  return track.points.map((point) => `${point.image_point_x},${point.image_point_y}`).join(' ')
}

function visibleDetections() {
  return (props.detections ?? []).filter((detection) => props.frameIndex === undefined || detection.frame_index === props.frameIndex)
}
</script>

<template>
  <svg class="track-overlay" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" aria-label="Tracking overlay">
    <g v-for="track in tracks ?? []" :key="track.track_id" class="path">
      <polyline v-if="track.points.length" :points="pathForTrack(track)" />
    </g>
    <g v-for="detection in visibleDetections()" :key="detection.detection_id" class="bbox">
      <rect :x="detection.box.x" :y="detection.box.y" :width="detection.box.width" :height="detection.box.height" rx="1" />
      <text :x="detection.box.x" :y="Math.max(4, detection.box.y - 2)">
        {{ detection.track_id ?? detection.detection_id }} {{ Math.round(detection.confidence * 100) }}%
      </text>
    </g>
  </svg>
</template>

<style scoped>
.track-overlay {
  inset: 0;
  pointer-events: none;
  position: absolute;
}

.path polyline {
  fill: none;
  stroke: #facc15;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 0.7;
}

.bbox rect {
  fill: rgb(34 197 94 / 0.18);
  stroke: #22c55e;
  stroke-width: 0.6;
}

.bbox text {
  fill: white;
  font-size: 4px;
  paint-order: stroke;
  stroke: #0f172a;
  stroke-width: 0.5px;
}
</style>
