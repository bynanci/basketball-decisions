<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError, type ReferenceVideo } from '../api/client'

const referenceVideos = ref<ReferenceVideo[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const errorCode = ref('')
const form = ref({ title: '', url: '', tags: '', notes: '' })

function parseTags(value: string) {
  return value.split(',').map((tag) => tag.trim()).filter(Boolean)
}

function showError(error: unknown, fallback: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
  } else {
    errorCode.value = 'FRONTEND_ERROR'
    errorMessage.value = error instanceof Error ? error.message : fallback
  }
}

async function loadReferenceVideos() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.listReferenceVideos()
    referenceVideos.value = response.reference_videos
  } catch (error) {
    showError(error, 'Could not load reference videos.')
  } finally {
    isLoading.value = false
  }
}

async function createReferenceVideo() {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.createReferenceVideo({
      title: form.value.title,
      url: form.value.url,
      tags: parseTags(form.value.tags),
      notes: form.value.notes || null
    })
    form.value = { title: '', url: '', tags: '', notes: '' }
    statusMessage.value = 'Reference video registered as metadata only.'
    await loadReferenceVideos()
  } catch (error) {
    showError(error, 'Could not create the reference video.')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadReferenceVideos)
</script>

<template>
  <section class="card reference-hero">
    <p class="eyebrow">Reference Video Breakdown Importer</p>
    <h1>Register teaching clips without downloading media</h1>
    <p>
      Save YouTube or web video links as source-governed reference metadata, then manually extract concepts and coaching reads on the detail page.
      These sources stay reference-only and are not training eligible.
    </p>
    <p v-if="statusMessage" class="success-message">{{ statusMessage }}</p>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
    </div>
  </section>

  <section class="card">
    <p class="eyebrow">Create</p>
    <h2>Add a reference video</h2>
    <form class="reference-form" @submit.prevent="createReferenceVideo">
      <label>
        Title
        <input v-model="form.title" required placeholder="Example: Spain PnR weak-side read" />
      </label>
      <label>
        URL
        <input v-model="form.url" required type="url" placeholder="https://www.youtube.com/watch?v=…" />
      </label>
      <label>
        Tags
        <input v-model="form.tags" placeholder="pick-and-roll, weak-side, teaching" />
      </label>
      <label>
        Notes
        <textarea v-model="form.notes" rows="3" placeholder="Why this clip is useful…" />
      </label>
      <button type="submit" :disabled="isSaving">{{ isSaving ? 'Saving…' : 'Register Reference Video' }}</button>
    </form>
  </section>

  <section class="card">
    <div class="table-header">
      <div>
        <p class="eyebrow">Library</p>
        <h2>Reference videos</h2>
      </div>
      <span>{{ referenceVideos.length }} videos</span>
    </div>
    <p v-if="isLoading">Loading reference videos…</p>
    <div v-else class="reference-list">
      <article v-for="video in referenceVideos" :key="video.reference_id" class="reference-card">
        <div>
          <h3><RouterLink :to="`/reference-videos/${video.reference_id}`">{{ video.title }}</RouterLink></h3>
          <a :href="video.url" target="_blank" rel="noreferrer">{{ video.url }}</a>
          <p v-if="video.notes" class="muted">{{ video.notes }}</p>
          <div class="tag-row"><span v-for="tag in video.tags" :key="tag">{{ tag }}</span></div>
        </div>
        <div class="badge-column">
          <span class="warning-badge">{{ video.usage_scope }}</span>
          <span class="danger-badge">NOT TRAINING ELIGIBLE</span>
        </div>
      </article>
      <p v-if="referenceVideos.length === 0">No reference videos registered yet.</p>
    </div>
  </section>
</template>

<style scoped>
.reference-hero,
.reference-form,
.reference-list {
  display: grid;
  gap: 1rem;
}

.reference-form label {
  display: grid;
  gap: 0.35rem;
  font-weight: 700;
}

.reference-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  padding: 1rem;
}

.reference-card h3 {
  margin-top: 0;
}

.badge-column,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.badge-column {
  align-content: flex-start;
  justify-content: flex-end;
}

.tag-row span,
.warning-badge,
.danger-badge {
  border-radius: 999px;
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.2rem 0.55rem;
}

.tag-row span {
  background: #e0f2fe;
  color: #075985;
}

.warning-badge {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.danger-badge {
  background: #fee2e2;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.table-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}
</style>
