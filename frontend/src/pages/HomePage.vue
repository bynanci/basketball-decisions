<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import { useProjectStore } from '../stores/projectStore'
import { useRoleStore } from '../stores/roleStore'

const router = useRouter()
const projectStore = useProjectStore()
const roleStore = useRoleStore()
const projectName = ref('Demo Project')
const youtubeUrl = ref('')
const youtubeRightsConfirmed = ref(false)
const canSubmitYouTube = computed(() => youtubeUrl.value.trim().length > 0 && youtubeRightsConfirmed.value && !isSubmitting.value)
const selectedFile = ref<File | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')
const sampleStatus = ref<Awaited<ReturnType<typeof apiClient.getSampleDataStatus>> | null>(null)
const isLoadingSample = ref(false)
const sampleMessage = ref('')

const sampleQuickLinks = computed(() => sampleStatus.value?.quick_links ?? [])

const journeyCards = [
  {
    title: 'Start as Coach',
    eyebrow: 'Coach journey',
    description: 'Review coach reports, choose drills, and turn evidence into practice plans.',
    to: '/reports/coach',
    cta: 'Open coach reports'
  },
  {
    title: 'Start as Analyst',
    eyebrow: 'Analyst journey',
    description: 'Triage project health, review artifacts, and move video through the analysis pipeline.',
    to: '/development-dashboard',
    cta: 'Open command center'
  },
  {
    title: 'Start as Player',
    eyebrow: 'Player journey',
    description: 'Pick a role, preview situations, and practice role-specific decision reads.',
    to: '/start',
    cta: 'Choose player role'
  }
]

function isInternalLink(href: string) {
  return href.startsWith('/')
}

onMounted(() => {
  void loadSampleStatus()
})

async function loadSampleStatus() {
  try {
    sampleStatus.value = await apiClient.getSampleDataStatus()
  } catch (error) {
    showError(error, 'Could not load sample project status.')
  }
}

async function loadSampleProject() {
  if (isLoadingSample.value) return
  isLoadingSample.value = true
  sampleMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.seedSampleData()
    sampleStatus.value = response
    sampleMessage.value = response.message
    const bundle = await apiClient.getProjectBundle(response.project_id)
    projectStore.hydrateProjectFromBundle(bundle)
    router.push(`/projects/${response.project_id}`)
  } catch (error) {
    showError(error, 'Could not install the sample project.')
  } finally {
    isLoadingSample.value = false
  }
}


const recommendedSituations = computed(() => {
  if (!roleStore.roleProfile?.situationTypes.length) {
    return ['Pick and Roll', 'Drive and Kick', 'Help Rotation']
  }

  return roleStore.roleProfile.situationTypes.slice(0, 4).map(formatRole)
})

function formatRole(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(' ')
}

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
  <section class="card hero-card">
    <p class="eyebrow">Court IQ</p>
    <h1>Basketball video decision pipeline</h1>
    <p>Create a project from a local MP4 or YouTube URL, calibrate court keypoints manually, then inspect tracking overlays and a 2D projection.</p>
    <RouterLink class="button" to="/start">Choose training role</RouterLink>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
      <small v-if="errorHint">{{ errorHint }}</small>
    </div>
  </section>

  <section class="journey-card-grid" aria-label="Core user journey shortcuts">
    <article v-for="journey in journeyCards" :key="journey.title" class="card journey-card">
      <p class="eyebrow">{{ journey.eyebrow }}</p>
      <h2>{{ journey.title }}</h2>
      <p>{{ journey.description }}</p>
      <RouterLink class="button" :to="journey.to">{{ journey.cta }}</RouterLink>
    </article>
  </section>

  <section class="card sample-project-card" data-testid="sample-data-card">
    <div>
      <p class="eyebrow">Sample dataset</p>
      <h2>Load Sample Project <span v-if="sampleStatus?.installed" class="sample-badge">Sample installed</span></h2>
      <p>Install a deterministic, metadata-only pick-and-roll sample. It uses synthetic frame artwork, does not download videos, and is marked demo-only.</p>
      <p v-if="sampleStatus" class="muted">{{ sampleStatus.message }} · {{ sampleStatus.artifact_count }} artifacts present.</p>
      <p v-if="sampleMessage" class="success-message">{{ sampleMessage }}</p>
    </div>
    <div class="sample-actions">
      <button type="button" data-testid="seed-sample-data" :disabled="isLoadingSample || sampleStatus?.protected_existing_project" @click="loadSampleProject">
        {{ isLoadingSample ? 'Installing…' : sampleStatus?.installed ? 'Open / refresh sample project' : 'Load Sample Project' }}
      </button>
      <span v-if="sampleStatus?.protected_existing_project" class="error-text">A non-sample project already uses the sample id.</span>
    </div>
    <div v-if="sampleQuickLinks.length" class="quick-links sample-links">
      <template v-for="link in sampleQuickLinks" :key="link.href">
        <RouterLink v-if="isInternalLink(link.href)" :to="link.href">{{ link.label }}</RouterLink>
        <a v-else :href="link.href">{{ link.label }}</a>
      </template>
    </div>
  </section>

  <section v-if="roleStore.roleProfile" class="card role-mode-card">
    <div>
      <p class="eyebrow">Current mode</p>
      <h2>Current mode: {{ roleStore.roleProfile.userRole }} / {{ roleStore.roleProfile.courtRole }}</h2>
      <p>Open the training lobby to see quiz prompts filtered for your selected role and situations.</p>
    </div>
    <div class="quick-links">
      <RouterLink to="/training">Training lobby</RouterLink>
      <a href="#project-creation">Continue projects</a>
      <RouterLink to="/start">Change role</RouterLink>
    </div>
    <div class="recommendation-list">
      <strong>Recommended situations</strong>
      <ul>
        <li v-for="situation in recommendedSituations" :key="situation">{{ situation }}</li>
      </ul>
    </div>
  </section>

  <section id="project-creation" class="grid">
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

<style scoped>
.journey-card-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  margin-bottom: 1rem;
}

.journey-card {
  display: flex;
  flex-direction: column;
}

.journey-card .button {
  align-self: flex-start;
  margin-top: auto;
}

.sample-project-card {
  display: grid;
  gap: 1rem;
}

.sample-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.sample-badge {
  background: #dbeafe;
  border: 1px solid #60a5fa;
  border-radius: 999px;
  color: #1d4ed8;
  display: inline-flex;
  font-size: 0.75rem;
  font-weight: 800;
  margin-left: 0.5rem;
  padding: 0.2rem 0.55rem;
  text-transform: uppercase;
}

.sample-links {
  justify-content: flex-start;
}

.muted {
  color: #64748b;
}

.success-message {
  color: #166534;
  font-weight: 700;
}

.error-text {
  color: #b91c1c;
  font-weight: 700;
}
</style>
