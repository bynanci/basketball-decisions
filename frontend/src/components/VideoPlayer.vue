<script setup lang="ts">
defineProps<{
  src?: string
  title?: string
}>()
</script>

<template>
  <section class="video-frame">
    <video v-if="src" controls :src="src" />
    <div v-else class="placeholder">
      <strong>{{ title ?? 'Video preview' }}</strong>
      <span>Upload an MP4 or create a YouTube project to load a video.</span>
    </div>
  </section>
</template>

<style scoped>
.video-frame {
  align-items: center;
  aspect-ratio: 16 / 9;
  background: #111827;
  border-radius: 16px;
  color: white;
  display: flex;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

video {
  height: 100%;
  width: 100%;
}

.placeholder {
  display: grid;
  gap: 0.5rem;
  padding: 2rem;
  text-align: center;
}

.placeholder span {
  color: #cbd5e1;
}
</style>
