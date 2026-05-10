<script setup lang="ts">
import { ref } from 'vue'
import type { DecisionArrowPoint, DecisionQuizOption } from '../api/client'

const props = withDefaults(
  defineProps<{
    options: DecisionQuizOption[]
    readonly?: boolean
    selectedOptionId?: string | null
    correctOptionId?: string | null
    incorrectOptionId?: string | null
    disabled?: boolean
  }>(),
  { readonly: false, selectedOptionId: null, correctOptionId: null, incorrectOptionId: null, disabled: false }
)

const emit = defineEmits<{
  (event: 'create-arrow', payload: { start: DecisionArrowPoint; end: DecisionArrowPoint }): void
  (event: 'select-option', optionId: string): void
}>()

const drawingStart = ref<DecisionArrowPoint | null>(null)
const previewEnd = ref<DecisionArrowPoint | null>(null)
const labelOffset = 0.014

function clamp(value: number) {
  return Math.min(1, Math.max(0, value))
}

function pointerPoint(event: MouseEvent): DecisionArrowPoint {
  const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  return {
    x: clamp((event.clientX - rect.left) / rect.width),
    y: clamp((event.clientY - rect.top) / rect.height)
  }
}

function labelX(point: DecisionArrowPoint) {
  return clamp(point.x + labelOffset)
}

function labelY(point: DecisionArrowPoint) {
  return clamp(point.y - labelOffset)
}

function optionClass(option: DecisionQuizOption) {
  return {
    selected: option.option_id === props.selectedOptionId,
    correct: option.option_id === props.correctOptionId,
    incorrect: option.option_id === props.incorrectOptionId
  }
}

function markerForOption(option: DecisionQuizOption) {
  if (option.option_id === props.correctOptionId) return 'url(#decision-arrowhead-correct)'
  if (option.option_id === props.incorrectOptionId) return 'url(#decision-arrowhead-incorrect)'
  if (option.option_id === props.selectedOptionId) return 'url(#decision-arrowhead-selected)'
  return 'url(#decision-arrowhead)'
}

function selectOption(optionId: string) {
  if (props.disabled) return
  emit('select-option', optionId)
}

function onPointerDown(event: MouseEvent) {
  if (props.readonly || props.disabled) return
  drawingStart.value = pointerPoint(event)
  previewEnd.value = drawingStart.value
}

function onPointerMove(event: MouseEvent) {
  if (!drawingStart.value || props.readonly || props.disabled) return
  previewEnd.value = pointerPoint(event)
}

function onPointerUp(event: MouseEvent) {
  if (!drawingStart.value || props.readonly || props.disabled) return
  const end = pointerPoint(event)
  const start = drawingStart.value
  drawingStart.value = null
  previewEnd.value = null
  if (Math.abs(end.x - start.x) < 0.01 && Math.abs(end.y - start.y) < 0.01) return
  emit('create-arrow', { start, end })
}
</script>

<template>
  <svg
    :class="['arrow-overlay', { disabled }]"
    viewBox="0 0 1 1"
    preserveAspectRatio="none"
    role="img"
    aria-label="Decision arrows"
    @mousedown.self="onPointerDown"
    @mousemove="onPointerMove"
    @mouseup="onPointerUp"
    @mouseleave="onPointerUp"
  >
    <defs>
      <marker id="decision-arrowhead" markerWidth="14" markerHeight="10" refX="11" refY="5" orient="auto" markerUnits="strokeWidth">
        <path d="M 0 0 L 12 5 L 0 10 z" fill="#f97316" />
      </marker>
      <marker id="decision-arrowhead-selected" markerWidth="14" markerHeight="10" refX="11" refY="5" orient="auto" markerUnits="strokeWidth">
        <path d="M 0 0 L 12 5 L 0 10 z" fill="#3b82f6" />
      </marker>
      <marker id="decision-arrowhead-correct" markerWidth="14" markerHeight="10" refX="11" refY="5" orient="auto" markerUnits="strokeWidth">
        <path d="M 0 0 L 12 5 L 0 10 z" fill="#22c55e" />
      </marker>
      <marker id="decision-arrowhead-incorrect" markerWidth="14" markerHeight="10" refX="11" refY="5" orient="auto" markerUnits="strokeWidth">
        <path d="M 0 0 L 12 5 L 0 10 z" fill="#ef4444" />
      </marker>
    </defs>

    <g v-for="option in options" :key="option.option_id" class="arrow-hit-target" @click.stop="selectOption(option.option_id)">
      <line
        :x1="option.start.x"
        :y1="option.start.y"
        :x2="option.end.x"
        :y2="option.end.y"
        class="arrow-line-hit"
      />
      <line
        :x1="option.start.x"
        :y1="option.start.y"
        :x2="option.end.x"
        :y2="option.end.y"
        :class="['arrow-line', optionClass(option)]"
        :marker-end="markerForOption(option)"
      />
      <text
        :x="labelX(option.end)"
        :y="labelY(option.end)"
        :class="['arrow-label', optionClass(option)]"
      >
        {{ option.option_id }}. {{ option.label || 'Decision' }}
      </text>
    </g>

    <line
      v-if="drawingStart && previewEnd"
      :x1="drawingStart.x"
      :y1="drawingStart.y"
      :x2="previewEnd.x"
      :y2="previewEnd.y"
      class="arrow-line preview"
      marker-end="url(#decision-arrowhead)"
    />
  </svg>
</template>

<style scoped>
.arrow-overlay {
  cursor: crosshair;
  inset: 0;
  position: absolute;
  width: 100%;
  height: 100%;
}

.arrow-overlay.disabled {
  cursor: default;
}

.arrow-hit-target {
  cursor: pointer;
}

.arrow-overlay.disabled .arrow-hit-target {
  cursor: default;
}

.arrow-line-hit {
  stroke: transparent;
  stroke-linecap: round;
  stroke-width: 28px;
  vector-effect: non-scaling-stroke;
}

.arrow-line {
  fill: none;
  stroke: #f97316;
  stroke-linecap: round;
  stroke-width: 7px;
  vector-effect: non-scaling-stroke;
}

.arrow-line.selected {
  stroke: #3b82f6;
}

.arrow-line.correct {
  stroke: #22c55e;
}

.arrow-line.incorrect {
  stroke: #ef4444;
}

.arrow-line.preview {
  opacity: 0.7;
  stroke-dasharray: 14px 10px;
}

.arrow-label {
  fill: white;
  dominant-baseline: text-after-edge;
  font-size: 34px;
  font-weight: 800;
  paint-order: stroke;
  stroke: #111827;
  stroke-width: 7px;
  vector-effect: non-scaling-stroke;
}

.arrow-label.selected {
  stroke: #1e3a8a;
}

.arrow-label.correct {
  stroke: #14532d;
}

.arrow-label.incorrect {
  stroke: #7f1d1d;
}
</style>
