<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    freezeFrameSrc?: string | null
    frameLabel?: string
    directionLabel?: string
  }>(),
  {
    freezeFrameSrc: null,
    frameLabel: 'Freeze frame placeholder',
    directionLabel: 'Decision direction placeholder'
  }
)

// TODO: 尚未評分
// TODO: 尚未串教練標註
// TODO: 尚未處理多球員決策
</script>

<template>
  <section class="decision-quiz-overlay" aria-label="Decision quiz placeholder">
    <div class="freeze-frame" aria-label="Freeze frame">
      <img v-if="props.freezeFrameSrc" :src="props.freezeFrameSrc" :alt="props.frameLabel" />
      <div v-else class="freeze-frame-placeholder">
        <span>{{ props.frameLabel }}</span>
      </div>
    </div>

    <div class="direction-placeholder" aria-label="Direction arrow placeholder">
      <svg viewBox="0 0 100 100" role="img" aria-hidden="true">
        <line x1="18" y1="50" x2="76" y2="50" />
        <polyline points="58,30 78,50 58,70" />
      </svg>
      <p>{{ props.directionLabel }}</p>
    </div>
  </section>
</template>

<style scoped>
.decision-quiz-overlay {
  align-items: center;
  background: rgb(15 23 42 / 0.76);
  border: 1px dashed rgb(148 163 184 / 0.72);
  border-radius: 16px;
  color: #f8fafc;
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr) auto;
  inset: 1rem;
  padding: 1rem;
  pointer-events: none;
  position: absolute;
}

.freeze-frame {
  align-items: center;
  aspect-ratio: 16 / 9;
  background: #020617;
  border-radius: 12px;
  display: flex;
  justify-content: center;
  min-height: 10rem;
  overflow: hidden;
}

.freeze-frame img {
  height: 100%;
  object-fit: contain;
  width: 100%;
}

.freeze-frame-placeholder {
  align-items: center;
  background: linear-gradient(135deg, rgb(30 41 59), rgb(71 85 105));
  display: flex;
  font-weight: 700;
  height: 100%;
  justify-content: center;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  width: 100%;
}

.direction-placeholder {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 8rem;
  text-align: center;
}

.direction-placeholder svg {
  height: 5rem;
  width: 5rem;
}

.direction-placeholder line,
.direction-placeholder polyline {
  fill: none;
  stroke: #f97316;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 8;
}

.direction-placeholder p {
  color: #fed7aa;
  font-size: 0.85rem;
  font-weight: 700;
  margin: 0;
}
</style>
