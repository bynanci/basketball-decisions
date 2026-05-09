<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import Court2DView from '../components/Court2DView.vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
projectStore.setActiveProject(props.projectId)
const project = computed(() => projectStore.getProject(props.projectId))
const isExtracting = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')

function showError(error: unknown) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'FRAME_EXTRACTION_ERROR'
    errorMessage.value = 'Could not extract frames.'
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

async function extractFrames() {
  const videoAsset = project.value?.videoAsset
  if (!videoAsset || isExtracting.value) return
  isExtracting.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const response = await apiClient.extractFrames(props.projectId, {
      project_id: props.projectId,
      video_asset_id: videoAsset.asset_id,
      target_fps: 1,
      max_frames: 120
    })
    projectStore.setFrames(props.projectId, response.frames)
  } catch (error) {
    showError(error)
  } finally {
    isExtracting.value = false
  }
}
</script>

<template>
  <section class="card">
    <h1>{{ project?.name ?? 'Project' }}</h1>
    <p>Project id: {{ projectId }}</p>
    <p>Source: {{ project?.source ?? 'unknown' }} <span v-if="project?.videoFileName">· {{ project.videoFileName }}</span></p>
    <RouterLink class="button" :to="`/projects/${projectId}/calibration`">Calibrate court</RouterLink>
    <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Tracking</RouterLink>
  </section>

  <section v-if="errorMessage" class="error-card" role="alert">
    <strong>{{ errorCode }}</strong>
    <p>{{ errorMessage }}</p>
    <small v-if="errorHint">{{ errorHint }}</small>
  </section>

  <section class="grid">
    <div class="card">
      <h2>Video</h2>
      <VideoPlayer :video-src="project?.videoPreviewUrl" :title="project?.videoFileName ?? project?.youtubeUrl ?? 'No video selected'" />
      <button type="button" class="extract-button" :disabled="!project?.videoAsset || isExtracting" @click="extractFrames">
        {{ isExtracting ? 'Extracting…' : 'Extract Frames' }}
      </button>
      <p v-if="!project?.videoAsset" class="muted">Upload or import a video before extracting frames.</p>
    </div>
    <div class="card">
      <h2>Projected court</h2>
      <Court2DView :projected-tracks="project?.projectedTracks" />
    </div>
  </section>

  <section class="card">
    <h2>Extracted frames</h2>
    <p v-if="!project?.frames.length" class="muted">No extracted frames yet. Click Extract Frames after uploading an MP4.</p>
    <div v-else class="frame-strip">
      <article v-for="frame in project.frames" :key="frame.frame_id" class="frame-card">
        <img :src="apiClient.frameImageUrl(projectId, frame.frame_index)" :alt="`Frame ${frame.frame_index}`" />
        <strong>Frame {{ frame.frame_index }}</strong>
        <span>{{ frame.timestamp_seconds.toFixed(2) }}s</span>
        <RouterLink class="button small" :to="`/projects/${projectId}/calibration?frameIndex=${frame.frame_index}`">Use for calibration</RouterLink>
      </article>
    </div>
  </section>
</template>

<style scoped>
.secondary {
  background: #475569;
  margin-left: 0.75rem;
}

.extract-button {
  margin-top: 1rem;
}

.frame-strip {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.frame-card {
  border: 1px solid #dde3ee;
  border-radius: 12px;
  display: grid;
  flex: 0 0 180px;
  gap: 0.35rem;
  padding: 0.75rem;
}

.frame-card img {
  aspect-ratio: 16 / 9;
  background: #111827;
  border-radius: 8px;
  object-fit: cover;
  width: 100%;
}

.small {
  font-size: 0.85rem;
  padding: 0.5rem 0.65rem;
  text-align: center;
}

.muted {
  color: #64748b;
}
</style>
