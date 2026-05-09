<script setup lang="ts">
defineProps<{
  videoSrc?: string
  frameSrc?: string
  title?: string
  caption?: string
}>()
</script>

<template>
  <section class="video-frame">
    <img v-if="frameSrc" :src="frameSrc" :alt="title ?? 'Frame preview'" />
    <video v-else-if="videoSrc" controls :src="videoSrc" />
    <div v-else class="placeholder">
      <strong>{{ title ?? 'Video preview' }}</strong>
      <span>{{ caption ?? 'Upload an MP4, extract a frame, or create a YouTube project to load a preview.' }}</span>
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

video,
img {
  display: block;
  height: 100%;
  object-fit: contain;
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
