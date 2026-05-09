<script setup lang="ts">
import type { ProjectedPlayerTrack } from '../api/client'

interface PlayerPoint {
  id: string
  team: 'home' | 'away' | 'unknown'
  x: number
  y: number
}

defineProps<{
  players?: PlayerPoint[]
  projectedTracks?: ProjectedPlayerTrack[]
}>()

function trackPath(track: ProjectedPlayerTrack) {
  return track.points.map((point) => `${point.court_x},${point.court_y}`).join(' ')
}
</script>

<template>
  <figure class="court-figure">
    <svg class="court" viewBox="0 0 94 50" role="img" aria-label="2D basketball court">
    <rect x="1" y="1" width="92" height="48" rx="1" />
    <line x1="47" y1="1" x2="47" y2="49" />
    <circle cx="47" cy="25" r="6" />
    <circle cx="47" cy="25" r="1" />
    <rect x="1" y="17" width="19" height="16" />
    <rect x="74" y="17" width="19" height="16" />
    <path d="M20 19 A6 6 0 0 1 20 31" />
    <path d="M74 19 A6 6 0 0 0 74 31" />
    <path d="M14 4 A23 23 0 0 1 14 46" />
    <path d="M80 4 A23 23 0 0 0 80 46" />
    <g v-for="track in projectedTracks ?? []" :key="track.track_id" class="projected-track">
      <polyline v-if="track.points.length" :points="trackPath(track)" />
      <circle
        v-if="track.points.length"
        :cx="track.points[track.points.length - 1].court_x"
        :cy="track.points[track.points.length - 1].court_y"
        r="1.5"
      />
      <text
        v-if="track.points.length"
        :x="track.points[track.points.length - 1].court_x + 1.8"
        :y="track.points[track.points.length - 1].court_y - 1.8"
      >
        {{ track.player_id ?? track.track_id }}
      </text>
    </g>
    <g v-for="player in players ?? []" :key="player.id">
      <circle class="player" :class="player.team" :cx="player.x" :cy="player.y" r="1.6" />
    </g>
    </svg>
    <figcaption>Projected backend court coordinates are rendered in court feet on a 94 × 50 ft viewBox.</figcaption>
  </figure>
</template>

<style scoped>
.court-figure {
  margin: 0;
}

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

.projected-track polyline {
  fill: none;
  stroke: #2563eb;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 0.8;
}

.projected-track circle {
  fill: #2563eb;
  stroke: white;
  stroke-width: 0.3;
}

.projected-track text {
  fill: #111827;
  font-size: 3px;
  font-weight: 700;
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
figcaption {
  color: #64748b;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}
</style>
