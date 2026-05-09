<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import VideoPlayer from '../components/VideoPlayer.vue'
import Court2DView from '../components/Court2DView.vue'
import { useProjectsStore } from '../stores/projects'

const props = defineProps<{
  projectId: string
}>()

const projectsStore = useProjectsStore()
const project = computed(() => projectsStore.projects.find((item) => item.id === props.projectId))
</script>

<template>
  <section class="card">
    <h1>{{ project?.name ?? 'Project' }}</h1>
    <p>Source: {{ project?.source ?? 'unknown' }}</p>
    <RouterLink class="button" :to="`/projects/${projectId}/calibration`">Calibrate court</RouterLink>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Tracking demo</RouterLink>
  </section>

  <section class="grid">
    <div class="card">
      <h2>Video</h2>
      <VideoPlayer :title="project?.videoPath ?? project?.youtubeUrl ?? 'No video selected'" />
    </div>
    <div class="card">
      <h2>Projected court</h2>
      <Court2DView />
    </div>
  </section>
</template>

<style scoped>
.secondary {
  background: #475569;
  margin-left: 0.75rem;
}
</style>
