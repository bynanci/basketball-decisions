<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '../stores/projects'

const router = useRouter()
const projectsStore = useProjectsStore()
const projectName = ref('Demo Project')
const youtubeUrl = ref('')
const selectedFile = ref<File | null>(null)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function createUploadProject() {
  const id = crypto.randomUUID()
  projectsStore.addProject({
    id,
    name: projectName.value,
    source: 'upload',
    videoPath: selectedFile.value?.name
  })
  router.push(`/projects/${id}`)
}

function createYoutubeProject() {
  const id = crypto.randomUUID()
  projectsStore.addProject({
    id,
    name: projectName.value,
    source: 'youtube',
    youtubeUrl: youtubeUrl.value
  })
  router.push(`/projects/${id}`)
}
</script>

<template>
  <section class="card">
    <h1>Basketball video decision pipeline</h1>
    <p>Create a project from a local MP4 or YouTube URL, calibrate the court, then run a tracking demo.</p>
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
        <input v-model="youtubeUrl" placeholder="https://www.youtube.com/watch?v=..." />
      </label>
      <button type="submit">Create YouTube project</button>
    </form>
  </section>
</template>
