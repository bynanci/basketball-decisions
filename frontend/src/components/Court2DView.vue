<script setup lang="ts">
interface PlayerPoint {
  id: string
  team: 'home' | 'away' | 'unknown'
  x: number
  y: number
}

defineProps<{
  players?: PlayerPoint[]
}>()
</script>

<template>
  <svg class="court" viewBox="0 0 94 50" role="img" aria-label="2D basketball court">
    <rect x="1" y="1" width="92" height="48" rx="1" />
    <line x1="47" y1="1" x2="47" y2="49" />
    <circle cx="47" cy="25" r="6" />
    <rect x="1" y="17" width="19" height="16" />
    <rect x="74" y="17" width="19" height="16" />
    <path d="M14 4 A23 23 0 0 1 14 46" />
    <path d="M80 4 A23 23 0 0 0 80 46" />
    <g v-for="player in players ?? []" :key="player.id">
      <circle class="player" :class="player.team" :cx="player.x" :cy="player.y" r="1.6" />
    </g>
  </svg>
</template>

<style scoped>
.court {
  background: #f8d49b;
  border-radius: 12px;
  max-width: 100%;
}

rect,
line,
path,
.court > circle {
  fill: none;
  stroke: #7c2d12;
  stroke-width: 0.6;
}

.player.home {
  fill: #2563eb;
}

.player.away {
  fill: #dc2626;
}

.player.unknown {
  fill: #64748b;
}
</style>
