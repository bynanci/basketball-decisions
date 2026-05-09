<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '../stores/projectStore'

const router = useRouter()
const projectStore = useProjectStore()
const projectName = ref('Demo Project')
const youtubeUrl = ref('')
const youtubeRightsConfirmed = ref(false)
const canSubmitYouTube = computed(() => youtubeUrl.value.trim().length > 0 && youtubeRightsConfirmed.value)
const selectedFile = ref<File | null>(null)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function createUploadProject() {
  const id = crypto.randomUUID()
  const previewUrl = selectedFile.value ? URL.createObjectURL(selectedFile.value) : undefined
  projectStore.addProject({
    id,
    name: projectName.value,
    source: 'upload',
    videoPreviewUrl: previewUrl,
    videoFileName: selectedFile.value?.name,
    videoAsset: selectedFile.value
      ? {
          project_id: id,
          asset_id: `local-${id}`,
          source_type: 'upload',
          filename: selectedFile.value.name,
          content_type: selectedFile.value.type
        }
      : null
  })
  router.push(`/projects/${id}`)
}

function createYoutubeProject() {
  if (!canSubmitYouTube.value) return

  const id = crypto.randomUUID()
  projectStore.addProject({
    id,
    name: projectName.value,
    source: 'youtube',
    youtubeUrl: youtubeUrl.value.trim()
  })
  router.push(`/projects/${id}`)
}
</script>

<template>
  <section class="card">
    <h1>Basketball video decision pipeline</h1>
    <p>Create a project from a local MP4 or YouTube URL, calibrate court keypoints manually, then inspect tracking overlays and a 2D projection.</p>
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
        <input type="file" accept="video/mp4" @change="onFileChange" />
      </label>
      <button type="submit">Create upload project</button>
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
      <button type="submit" :disabled="!canSubmitYouTube">Create YouTube project</button>
    </form>
  </section>
</template>
