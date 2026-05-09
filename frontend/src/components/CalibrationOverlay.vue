<script setup lang="ts">
interface Keypoint {
  id: string
  label: string
  x: number
  y: number
}

defineProps<{
  keypoints: Keypoint[]
}>()
</script>

<template>
  <svg class="overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Court calibration overlay">
    <line x1="5" y1="10" x2="95" y2="10" />
    <line x1="5" y1="90" x2="95" y2="90" />
    <line x1="5" y1="10" x2="5" y2="90" />
    <line x1="95" y1="10" x2="95" y2="90" />
    <g v-for="point in keypoints" :key="point.id">
      <circle :cx="point.x" :cy="point.y" r="2.5" />
      <text :x="point.x + 3" :y="point.y - 2">{{ point.label }}</text>
    </g>
  </svg>
</template>

<style scoped>
.overlay {
  inset: 0;
  pointer-events: none;
  position: absolute;
}

line {
  stroke: #38bdf8;
  stroke-width: 0.6;
}

circle {
  fill: #f97316;
  stroke: white;
  stroke-width: 0.4;
}

text {
  fill: white;
  font-size: 4px;
  paint-order: stroke;
  stroke: #0f172a;
  stroke-width: 0.5px;
}
</style>
