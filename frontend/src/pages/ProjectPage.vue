<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Court2DView from '../components/Court2DView.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)
const project = computed(() => projectStore.getProject(props.projectId))
</script>

<template>
  <section class="card">
    <h1>{{ project?.name ?? 'Project' }}</h1>
    <p>Project id: {{ projectId }}</p>
    <p>Source: {{ project?.source ?? 'unknown' }} <span v-if="project?.videoFileName">· {{ project.videoFileName }}</span></p>
    <RouterLink class="button" :to="`/projects/${projectId}/calibration`">Calibrate court</RouterLink>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Tracking demo</RouterLink>
  </section>

  <section class="grid">
    <div class="card">
      <h2>Video</h2>
      <VideoPlayer :video-src="project?.videoPreviewUrl" :title="project?.videoFileName ?? project?.youtubeUrl ?? 'No video selected'" />
    </div>
    <div class="card">
      <h2>Projected court</h2>
      <Court2DView :projected-tracks="project?.projectedTracks" />
    </div>
  </section>
</template>

<style scoped>
.secondary {
  background: #475569;
  margin-left: 0.75rem;
}
</style>
