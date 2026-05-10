<script setup lang="ts">
import { computed } from 'vue'
import type { CourtRole } from '../types/roles'

interface HighlightShape {
  type: 'rect' | 'circle' | 'path'
  label: string
  className: string
  x?: number
  y?: number
  width?: number
  height?: number
  cx?: number
  cy?: number
  r?: number
  d?: string
}

interface ArrowShape {
  d: string
  label: string
  className?: string
}

interface PlayerDot {
  cx: number
  cy: number
  label: string
  className?: string
}

interface RolePreviewConfig {
  title: string
  attentionText: string
  highlights: HighlightShape[]
  arrows: ArrowShape[]
  players: PlayerDot[]
}

const props = defineProps<{
  courtRole: CourtRole
}>()

const rolePreviewConfig: Record<CourtRole, RolePreviewConfig> = {
  BALL_HANDLER: {
    title: 'Ball handler read map',
    attentionText: 'Read the screen defender, low man, and weak-side corner.',
    highlights: [
      { type: 'circle', label: 'Ball handler area', className: 'primary-highlight', cx: 32, cy: 25, r: 7.5 },
      { type: 'path', label: 'Passing lanes', className: 'passing-highlight', d: 'M33 24 L8 8 L33 24 L8 42 L33 24 L66 12' },
      { type: 'path', label: 'Drive lanes', className: 'drive-highlight', d: 'M34 25 C48 19 59 17 72 25 M34 25 C48 31 59 33 72 25' }
    ],
    arrows: [
      { d: 'M34 25 C48 19 59 17 72 25', label: 'Middle drive lane', className: 'drive-arrow' },
      { d: 'M34 25 L8 8', label: 'Skip to corner', className: 'pass-arrow' },
      { d: 'M34 25 L66 12', label: 'Hit weak-side wing', className: 'pass-arrow' }
    ],
    players: [
      { cx: 32, cy: 25, label: 'BH', className: 'primary-player' },
      { cx: 43, cy: 25, label: 'SC' },
      { cx: 8, cy: 8, label: 'C' },
      { cx: 8, cy: 42, label: 'C' },
      { cx: 72, cy: 25, label: 'R' }
    ]
  },
  OFF_BALL_SHOOTER: {
    title: 'Shooter spacing map',
    attentionText: 'Keep spacing, lift when defender helps, relocate after drive.',
    highlights: [
      { type: 'rect', label: 'Corner relocation zone', className: 'primary-highlight', x: 3, y: 4, width: 12, height: 12 },
      { type: 'rect', label: 'Corner relocation zone', className: 'primary-highlight', x: 3, y: 34, width: 12, height: 12 },
      { type: 'rect', label: 'Wing lift zone', className: 'secondary-highlight', x: 16, y: 7, width: 17, height: 12 },
      { type: 'rect', label: 'Wing lift zone', className: 'secondary-highlight', x: 16, y: 31, width: 17, height: 12 }
    ],
    arrows: [
      { d: 'M8 42 C13 36 19 32 27 30', label: 'Lift on help', className: 'relocate-arrow' },
      { d: 'M27 30 C22 23 17 18 10 11', label: 'Relocate after drive', className: 'relocate-arrow' }
    ],
    players: [
      { cx: 8, cy: 42, label: 'SH', className: 'primary-player' },
      { cx: 37, cy: 25, label: 'BH' },
      { cx: 72, cy: 25, label: 'R' }
    ]
  },
  ROLLER: {
    title: 'Roller decision map',
    attentionText: 'Read pocket pass timing and weak-side low man.',
    highlights: [
      { type: 'rect', label: 'Short roll pocket', className: 'primary-highlight', x: 46, y: 18, width: 13, height: 14 },
      { type: 'circle', label: 'Rim roll finish zone', className: 'secondary-highlight', cx: 74, cy: 25, r: 8 }
    ],
    arrows: [
      { d: 'M42 25 C50 22 55 22 59 25', label: 'Short roll path', className: 'roll-arrow' },
      { d: 'M42 25 C55 30 66 30 75 25', label: 'Rim roll path', className: 'roll-arrow' }
    ],
    players: [
      { cx: 42, cy: 25, label: 'R', className: 'primary-player' },
      { cx: 31, cy: 25, label: 'BH' },
      { cx: 75, cy: 25, label: 'RIM' },
      { cx: 70, cy: 39, label: 'LM' }
    ]
  },
  SCREENER: {
    title: 'Screener angle map',
    attentionText: 'Set the angle, feel the defender, then choose rescreen, slip, or roll timing.',
    highlights: [
      { type: 'circle', label: 'Screen contact zone', className: 'primary-highlight', cx: 40, cy: 25, r: 7 },
      { type: 'rect', label: 'Separation window', className: 'secondary-highlight', x: 45, y: 18, width: 16, height: 14 }
    ],
    arrows: [
      { d: 'M40 25 C47 20 55 19 62 23', label: 'Slip or roll', className: 'roll-arrow' }
    ],
    players: [
      { cx: 40, cy: 25, label: 'SC', className: 'primary-player' },
      { cx: 30, cy: 25, label: 'BH' }
    ]
  },
  ON_BALL_DEFENDER: {
    title: 'Point-of-attack map',
    attentionText: 'Contain the ball, navigate the screen, and contest without opening the paint.',
    highlights: [
      { type: 'circle', label: 'Containment area', className: 'primary-highlight', cx: 32, cy: 25, r: 8 },
      { type: 'path', label: 'Screen navigation lane', className: 'secondary-highlight', d: 'M31 25 C38 18 45 18 52 24' }
    ],
    arrows: [
      { d: 'M31 25 C38 18 45 18 52 24', label: 'Fight over screen', className: 'defense-arrow' }
    ],
    players: [
      { cx: 32, cy: 25, label: 'D', className: 'primary-player' },
      { cx: 29, cy: 25, label: 'BH' }
    ]
  },
  HELP_DEFENDER: {
    title: 'Help defender stunt map',
    attentionText: 'Stunt, recover, and avoid overhelping.',
    highlights: [
      { type: 'circle', label: 'Nail help zone', className: 'primary-highlight', cx: 47, cy: 25, r: 6 },
      { type: 'rect', label: 'Paint help zone', className: 'secondary-highlight', x: 63, y: 17, width: 17, height: 16 }
    ],
    arrows: [
      { d: 'M55 13 C50 18 48 21 47 25', label: 'Stunt to nail', className: 'defense-arrow' },
      { d: 'M47 25 C50 20 53 16 55 13', label: 'Recover back', className: 'recover-arrow' }
    ],
    players: [
      { cx: 55, cy: 13, label: 'HD', className: 'primary-player' },
      { cx: 31, cy: 25, label: 'BH' },
      { cx: 73, cy: 25, label: 'R' }
    ]
  },
  LOW_MAN: {
    title: 'Low-man decision map',
    attentionText: 'Decide whether to tag roller or stay attached to corner shooter.',
    highlights: [
      { type: 'circle', label: 'Rim protection zone', className: 'primary-highlight', cx: 74, cy: 25, r: 8 },
      { type: 'rect', label: 'Weak-side corner', className: 'secondary-highlight', x: 3, y: 34, width: 13, height: 12 }
    ],
    arrows: [
      { d: 'M16 38 C34 39 57 34 72 27', label: 'Tag roller path', className: 'defense-arrow' },
      { d: 'M28 35 C20 37 14 39 8 42', label: 'Stay attached to corner', className: 'recover-arrow' }
    ],
    players: [
      { cx: 22, cy: 36, label: 'LM', className: 'primary-player' },
      { cx: 8, cy: 42, label: 'SH' },
      { cx: 73, cy: 25, label: 'R' }
    ]
  },
  TRAILER: {
    title: 'Trailer arrival map',
    attentionText: 'Arrive with spacing, flow into an early drag screen, or trail for the reversal three.',
    highlights: [
      { type: 'rect', label: 'Trail slot', className: 'primary-highlight', x: 30, y: 17, width: 17, height: 16 },
      { type: 'circle', label: 'Drag screen area', className: 'secondary-highlight', cx: 47, cy: 25, r: 6 }
    ],
    arrows: [
      { d: 'M20 25 C28 25 36 25 45 25', label: 'Flow into drag', className: 'roll-arrow' }
    ],
    players: [
      { cx: 20, cy: 25, label: 'TR', className: 'primary-player' },
      { cx: 36, cy: 20, label: 'BH' }
    ]
  },
  WEAK_SIDE_WING: {
    title: 'Weak-side wing map',
    attentionText: 'Hold spacing, lift behind help, cut when the low man turns, and be ready for the extra pass.',
    highlights: [
      { type: 'rect', label: 'Weak-side wing lift', className: 'primary-highlight', x: 14, y: 7, width: 19, height: 13 },
      { type: 'rect', label: 'Corner spacing', className: 'secondary-highlight', x: 3, y: 34, width: 13, height: 12 }
    ],
    arrows: [
      { d: 'M8 42 C14 34 20 25 29 17', label: 'Lift behind help', className: 'relocate-arrow' }
    ],
    players: [
      { cx: 8, cy: 42, label: 'W', className: 'primary-player' },
      { cx: 32, cy: 25, label: 'BH' }
    ]
  }
}

const preview = computed(() => rolePreviewConfig[props.courtRole])
</script>

<template>
  <article class="role-court-preview" :aria-label="`${preview.title}: ${preview.attentionText}`">
    <div class="preview-heading">
      <div>
        <p class="eyebrow">Role-aware court preview</p>
        <h2>{{ preview.title }}</h2>
      </div>
      <span class="role-pill">{{ courtRole.replace(/_/g, ' ') }}</span>
    </div>

    <svg class="court-svg" viewBox="0 0 94 50" role="img" :aria-labelledby="`court-title-${courtRole}`">
      <title :id="`court-title-${courtRole}`">{{ preview.title }}</title>
      <defs>
        <marker id="preview-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L6,3 z" class="arrow-head" />
        </marker>
      </defs>

      <rect class="court-floor" x="0.5" y="0.5" width="93" height="49" rx="2" />
      <line class="court-line" x1="47" y1="0.5" x2="47" y2="49.5" />
      <circle class="court-line no-fill" cx="47" cy="25" r="6" />
      <rect class="court-line no-fill" x="75" y="17" width="18" height="16" />
      <path class="court-line no-fill" d="M75 17 A8 8 0 0 0 75 33" />
      <circle class="court-line no-fill" cx="88" cy="25" r="1.5" />
      <path class="court-line no-fill" d="M75 3 C63 8 59 17 59 25 C59 33 63 42 75 47" />
      <line class="court-line" x1="94" y1="4" x2="80" y2="4" />
      <line class="court-line" x1="94" y1="46" x2="80" y2="46" />

      <g class="highlights">
        <template v-for="shape in preview.highlights" :key="shape.label + shape.className + (shape.d ?? shape.x ?? shape.cx)">
          <rect
            v-if="shape.type === 'rect'"
            :class="['highlight-shape', shape.className]"
            :x="shape.x"
            :y="shape.y"
            :width="shape.width"
            :height="shape.height"
            rx="3"
          >
            <title>{{ shape.label }}</title>
          </rect>
          <circle
            v-else-if="shape.type === 'circle'"
            :class="['highlight-shape', shape.className]"
            :cx="shape.cx"
            :cy="shape.cy"
            :r="shape.r"
          >
            <title>{{ shape.label }}</title>
          </circle>
          <path v-else :class="['highlight-path', shape.className]" :d="shape.d">
            <title>{{ shape.label }}</title>
          </path>
        </template>
      </g>

      <g class="arrows">
        <path v-for="arrow in preview.arrows" :key="arrow.label" :class="['role-arrow', arrow.className]" :d="arrow.d" marker-end="url(#preview-arrow)">
          <title>{{ arrow.label }}</title>
        </path>
      </g>

      <g class="players">
        <g v-for="player in preview.players" :key="`${player.label}-${player.cx}-${player.cy}`">
          <circle :class="['player-dot', player.className]" :cx="player.cx" :cy="player.cy" r="2.8" />
          <text class="player-label" :x="player.cx" :y="player.cy + 0.7" text-anchor="middle">{{ player.label }}</text>
        </g>
      </g>
    </svg>

    <div class="attention-card">
      <strong>Pay attention to</strong>
      <p>{{ preview.attentionText }}</p>
    </div>
  </article>
</template>

<style scoped>
.role-court-preview {
  display: grid;
  gap: 1rem;
}

.preview-heading {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.preview-heading h2 {
  margin: 0.15rem 0 0;
}

.role-pill {
  background: #ecfeff;
  border: 1px solid #67e8f9;
  border-radius: 999px;
  color: #155e75;
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.04em;
  padding: 0.45rem 0.7rem;
  text-transform: capitalize;
  white-space: nowrap;
}

.court-svg {
  background: #0f766e;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 18%);
  display: block;
  max-height: 540px;
  width: 100%;
}

.court-floor {
  fill: #f8c47b;
  stroke: #7c2d12;
  stroke-width: 0.55;
}

.court-line {
  fill: none;
  stroke: rgb(255 255 255 / 82%);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 0.45;
}

.no-fill {
  fill: none;
}

.highlight-shape {
  opacity: 0.72;
  stroke-width: 0.7;
}

.highlight-path {
  fill: none;
  opacity: 0.9;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.4;
}

.primary-highlight {
  fill: #22d3ee;
  stroke: #0e7490;
}

.secondary-highlight {
  fill: #a7f3d0;
  stroke: #047857;
}

.passing-highlight {
  stroke: #2563eb;
}

.drive-highlight,
.roll-arrow {
  stroke: #ea580c;
}

.role-arrow {
  fill: none;
  stroke: #1d4ed8;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.25;
}

.pass-arrow {
  stroke: #2563eb;
}

.drive-arrow {
  stroke: #ea580c;
}

.relocate-arrow {
  stroke: #7c3aed;
}

.defense-arrow {
  stroke: #dc2626;
}

.recover-arrow {
  stroke: #059669;
  stroke-dasharray: 2 1.4;
}

.arrow-head {
  fill: currentColor;
  color: #1d4ed8;
}

.player-dot {
  fill: #172554;
  stroke: white;
  stroke-width: 0.45;
}

.primary-player {
  fill: #be123c;
}

.player-label {
  fill: white;
  font-size: 2.15px;
  font-weight: 900;
  pointer-events: none;
}

.attention-card {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 14px;
  color: #9a3412;
  padding: 1rem;
}

.attention-card p {
  color: #7c2d12;
  font-size: 1.05rem;
  font-weight: 800;
  margin: 0.35rem 0 0;
}

@media (max-width: 720px) {
  .preview-heading {
    display: grid;
  }

  .role-pill {
    justify-self: start;
  }
}
</style>
