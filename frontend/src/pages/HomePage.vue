<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import { useProjectStore } from '../stores/projectStore'

const router = useRouter()
const projectStore = useProjectStore()
const projectName = ref('Demo Project')
const youtubeUrl = ref('')
const youtubeRightsConfirmed = ref(false)
const canSubmitYouTube = computed(() => youtubeUrl.value.trim().length > 0 && youtubeRightsConfirmed.value && !isSubmitting.value)
const selectedFile = ref<File | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function showError(error: unknown, fallback: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'FRONTEND_ERROR'
    errorMessage.value = fallback
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

async function createUploadProject() {
  if (!selectedFile.value || isSubmitting.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const projectResponse = await apiClient.createProject({ name: projectName.value.trim() || 'Untitled upload project' })
    const projectId = projectResponse.project.project_id
    const videoAsset = await apiClient.uploadVideo(projectId, selectedFile.value)
    const previewUrl = URL.createObjectURL(selectedFile.value)

    projectStore.addProject({
      id: projectId,
      name: projectResponse.project.name,
      source: 'upload',
      description: projectResponse.project.description,
      videoPreviewUrl: previewUrl,
      videoFileName: selectedFile.value.name,
      videoAsset
    })
    router.push(`/projects/${projectId}`)
  } catch (error) {
    showError(error, 'Could not create the upload project.')
  } finally {
    isSubmitting.value = false
  }
}

async function createYoutubeProject() {
  if (!canSubmitYouTube.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''

  try {
    const projectResponse = await apiClient.createProject({ name: projectName.value.trim() || 'Untitled YouTube project' })
    const projectId = projectResponse.project.project_id
    const videoAsset = await apiClient.createYouTubeVideo(projectId, { url: youtubeUrl.value.trim(), rights_confirmed: true })

    projectStore.addProject({
      id: projectId,
      name: projectResponse.project.name,
      source: 'youtube',
      description: projectResponse.project.description,
      youtubeUrl: youtubeUrl.value.trim(),
      videoAsset
    })
    router.push(`/projects/${projectId}`)
  } catch (error) {
    if (isApiClientError(error) && error.status === 501) {
      errorCode.value = error.code
      errorMessage.value = 'YouTube import is not available in this environment yet. Upload a local MP4 to continue the MVP flow.'
      errorHint.value = error.debug_hint ?? error.message
    } else {
      showError(error, 'Could not create the YouTube project.')
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="card">
    <h1>Basketball video decision pipeline</h1>
    <p>Create a project from a local MP4 or YouTube URL, calibrate court keypoints manually, then inspect tracking overlays and a 2D projection.</p>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
      <small v-if="errorHint">{{ errorHint }}</small>
    </div>
  </section>

  <section class="grid">
    <form class="card" @submit.prevent="createUploadProject">
      <h2>Local MP4</h2>
      <label>
        Project name
        <input v-model="projectName" required />
      </label>
      <label>
        MP4 file
        <input type="file" accept="video/mp4" required @change="onFileChange" />
      </label>
      <button type="submit" :disabled="!selectedFile || isSubmitting">{{ isSubmitting ? 'Creating…' : 'Create upload project' }}</button>
    </form>

    <form class="card" @submit.prevent="createYoutubeProject">
      <h2>YouTube URL</h2>
      <label>
        YouTube URL
        <input v-model="youtubeUrl" type="url" placeholder="https://www.youtube.com/watch?v=..." required />
      </label>
      <label class="checkbox-row">
        <input v-model="youtubeRightsConfirmed" type="checkbox" required />
        <span>I confirm I have the rights or permission to process this video.</span>
      </label>
      <button type="submit" :disabled="!canSubmitYouTube">{{ isSubmitting ? 'Creating…' : 'Create YouTube project' }}</button>
    </form>
  </section>
</template>
