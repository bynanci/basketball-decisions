<script setup lang="ts">
import { computed } from 'vue'
import type { CourtKeypointPair, CourtPoint } from '../api/client'

interface CourtKeypointOption {
  id: string
  label: string
  help: string
  courtPoint: CourtPoint
}

const props = defineProps<{
  keypoints: CourtKeypointOption[]
  pairs: CourtKeypointPair[]
  activeKeypointId: string
}>()

const emit = defineEmits<{
  addPoint: [pair: CourtKeypointPair]
  selectKeypoint: [keypointId: string]
  removePoint: [keypointId: string]
}>()

const activeKeypoint = computed(() => props.keypoints.find((point) => point.id === props.activeKeypointId))
const completedIds = computed(() => new Set(props.pairs.map((pair) => pair.keypoint_id)))
const waitingLabel = computed(() => activeKeypoint.value?.label ?? 'Select a court keypoint')

function onOverlayClick(event: MouseEvent) {
  if (!activeKeypoint.value) return
  const svg = event.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100
  emit('addPoint', {
    keypoint_id: activeKeypoint.value.id,
    image_point: { x, y },
    court_point: activeKeypoint.value.courtPoint,
    confidence: 1
  })
}
</script>

<template>
  <div class="calibration-panel">
    <p class="waiting">Waiting for: <strong>{{ waitingLabel }}</strong></p>
    <p v-if="activeKeypoint" class="hint">{{ activeKeypoint.help }} Click the matching spot on the frame.</p>
    <div class="keypoint-list" aria-label="Court keypoints">
      <button
        v-for="point in keypoints"
        :key="point.id"
        type="button"
        :class="{ active: point.id === activeKeypointId, done: completedIds.has(point.id) }"
        @click="emit('selectKeypoint', point.id)"
      >
        {{ point.label }}
      </button>
    </div>
  </div>

  <svg class="overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Court calibration overlay" @click="onOverlayClick">
    <rect class="click-surface" x="0" y="0" width="100" height="100" />
    <line x1="5" y1="10" x2="95" y2="10" />
    <line x1="5" y1="90" x2="95" y2="90" />
    <line x1="5" y1="10" x2="5" y2="90" />
    <line x1="95" y1="10" x2="95" y2="90" />
    <g v-for="pair in pairs" :key="pair.keypoint_id" class="marker" @click.stop="emit('removePoint', pair.keypoint_id)">
      <circle :cx="pair.image_point.x" :cy="pair.image_point.y" r="2.5" />
      <text :x="pair.image_point.x + 3" :y="pair.image_point.y - 2">{{ pair.court_point.label ?? pair.keypoint_id }}</text>
    </g>
  </svg>
</template>

<style scoped>
.calibration-panel {
  background: rgb(15 23 42 / 0.88);
  border-radius: 12px;
  color: white;
  left: 1rem;
  max-width: min(560px, calc(100% - 2rem));
  padding: 0.85rem;
  position: absolute;
  right: 1rem;
  top: 1rem;
  z-index: 2;
}

.waiting,
.hint {
  margin: 0 0 0.5rem;
}

.hint {
  color: #cbd5e1;
  font-size: 0.9rem;
}

.keypoint-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.keypoint-list button {
  background: #334155;
  padding: 0.45rem 0.7rem;
}

.keypoint-list button.active {
  background: #f97316;
}

.keypoint-list button.done {
  box-shadow: inset 0 -3px 0 #22c55e;
}

.overlay {
  cursor: crosshair;
  inset: 0;
  position: absolute;
}

.click-surface {
  fill: transparent;
}

line {
  stroke: #38bdf8;
  stroke-width: 0.6;
}

.marker {
  cursor: pointer;
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
