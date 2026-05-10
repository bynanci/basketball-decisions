<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { ListProjectsResponse, Project, QuizPrompt } from '../api/client'
import { useRoleStore } from '../stores/roleStore'

const roleStore = useRoleStore()
const projects = ref<ListProjectsResponse['projects']>([])
const selectedProjectId = ref('')
const prompts = ref<QuizPrompt[]>([])
const isLoadingProjects = ref(false)
const isLoadingPrompts = ref(false)
const projectErrorMessage = ref('')
const projectErrorCode = ref('')
const projectErrorHint = ref('')
const promptErrorMessage = ref('')
const promptErrorCode = ref('')
const promptErrorHint = ref('')

const roleProfile = computed(() => roleStore.roleProfile)
const selectedProject = computed(() => projects.value.find((project) => project.id === selectedProjectId.value) ?? null)
const selectedSituationsText = computed(() => {
  if (!roleProfile.value?.situationTypes.length) return 'All situations'
  return roleProfile.value.situationTypes.join(', ')
})
const matchLabel = computed(() => {
  if (!roleProfile.value) return ''
  const situationLabel = roleProfile.value.situationTypes.length ? roleProfile.value.situationTypes.join(', ') : 'ANY_SITUATION'
  return `${roleProfile.value.courtRole} / ${situationLabel}`
})
const recommendedPrompts = computed(() => {
  if (!roleProfile.value) return []
  const selectedSituations = roleProfile.value.situationTypes

  return prompts.value.filter((prompt) => {
    const matchesCourtRole = prompt.court_role_target === roleProfile.value?.courtRole
    const matchesSituation = selectedSituations.length === 0 || selectedSituations.includes(prompt.situation_type)
    const matchesUserRole = matchesPromptUserRole(prompt, roleProfile.value.userRole)
    return matchesCourtRole && matchesSituation && matchesUserRole
  })
})

onMounted(() => {
  if (roleProfile.value) {
    void loadProjects()
  }
})

watch(selectedProjectId, (projectId) => {
  if (projectId) {
    void loadPrompts(projectId)
  } else {
    prompts.value = []
  }
})

function formatRole(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(' ')
}

function matchesPromptUserRole(prompt: QuizPrompt, userRole: string) {
  const targetRoles = (prompt as unknown as { user_role_targets?: unknown }).user_role_targets
  if (!Array.isArray(targetRoles) || targetRoles.length === 0) return true

  const declaredUserRoles = targetRoles.filter((role): role is string =>
    typeof role === 'string' && ['COACH', 'PLAYER', 'ANALYST', 'FAN'].includes(role)
  )
  return declaredUserRoles.length === 0 || declaredUserRoles.includes(userRole)
}

function showApiError(error: unknown, fallbackCode: string, fallbackMessage: string, target: 'projects' | 'prompts') {
  const code = isApiClientError(error) ? error.code : fallbackCode
  const message = isApiClientError(error) ? error.message : fallbackMessage
  const hint = isApiClientError(error) ? error.debug_hint ?? '' : error instanceof Error ? error.message : ''

  if (target === 'projects') {
    projectErrorCode.value = code
    projectErrorMessage.value = message
    projectErrorHint.value = hint
  } else {
    promptErrorCode.value = code
    promptErrorMessage.value = message
    promptErrorHint.value = hint
  }
}

async function loadProjects() {
  isLoadingProjects.value = true
  projectErrorMessage.value = ''
  projectErrorCode.value = ''
  projectErrorHint.value = ''

  try {
    const response = await apiClient.listProjects()
    projects.value = response.projects
    selectedProjectId.value = response.projects[0]?.id ?? ''
  } catch (error) {
    projects.value = []
    selectedProjectId.value = ''
    showApiError(error, 'PROJECTS_LOAD_ERROR', 'Could not load projects.', 'projects')
  } finally {
    isLoadingProjects.value = false
  }
}

async function loadPrompts(projectId: Project['project_id']) {
  isLoadingPrompts.value = true
  promptErrorMessage.value = ''
  promptErrorCode.value = ''
  promptErrorHint.value = ''

  try {
    prompts.value = await apiClient.listQuizPrompts(projectId)
  } catch (error) {
    prompts.value = []
    showApiError(error, 'QUIZ_PROMPTS_LOAD_ERROR', 'Could not load quiz prompts.', 'prompts')
  } finally {
    isLoadingPrompts.value = false
  }
}
</script>

<template>
  <section v-if="!roleProfile" class="card hero-card">
    <p class="eyebrow">Training mode</p>
    <h1>Choose your role first</h1>
    <p>Select a role profile so Court IQ can recommend quiz prompts for your on-court decisions.</p>
    <RouterLink class="button" to="/start">Choose your role first</RouterLink>
  </section>

  <template v-else>
    <section class="card training-hero">
      <div>
        <p class="eyebrow">Training mode</p>
        <h1>{{ roleProfile.userRole }} / {{ roleProfile.courtRole }}</h1>
        <p>Recommended prompts are filtered by your court role and selected situations.</p>
      </div>
      <RouterLink class="button secondary-button" to="/start">Change role</RouterLink>
    </section>

    <section class="card profile-summary">
      <div>
        <strong>Current mode</strong>
        <span>{{ formatRole(roleProfile.userRole) }} / {{ formatRole(roleProfile.courtRole) }}</span>
      </div>
      <div>
        <strong>Selected situations</strong>
        <span>{{ selectedSituationsText }}</span>
      </div>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Prompt source</p>
          <h2>Choose a project</h2>
        </div>
        <button type="button" class="secondary-button" :disabled="isLoadingProjects" @click="loadProjects">
          {{ isLoadingProjects ? 'Refreshing…' : 'Refresh projects' }}
        </button>
      </div>

      <div v-if="projectErrorMessage" class="error-card" role="alert">
        <strong>{{ projectErrorCode }}</strong>
        <p>{{ projectErrorMessage }}</p>
        <small v-if="projectErrorHint">{{ projectErrorHint }}</small>
      </div>
      <p v-else-if="isLoadingProjects" class="muted">Loading projects…</p>
      <p v-else-if="!projects.length" class="muted">No projects are available yet. Create a project and build prompts from extracted frames.</p>
      <label v-else>
        Project
        <select v-model="selectedProjectId">
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }} ({{ project.id }})
          </option>
        </select>
      </label>
      <p v-if="selectedProject?.description" class="muted">{{ selectedProject.description }}</p>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Recommended for your role</p>
          <h2>Matching prompts</h2>
        </div>
        <span class="pill">{{ recommendedPrompts.length }} match{{ recommendedPrompts.length === 1 ? '' : 'es' }}</span>
      </div>

      <div v-if="promptErrorMessage" class="error-card" role="alert">
        <strong>{{ promptErrorCode }}</strong>
        <p>{{ promptErrorMessage }}</p>
        <small v-if="promptErrorHint">{{ promptErrorHint }}</small>
      </div>
      <p v-else-if="isLoadingPrompts" class="muted">Loading prompts…</p>
      <p v-else-if="selectedProjectId && !recommendedPrompts.length" class="empty-state">
        No prompts match {{ matchLabel }} yet. Build one from an extracted frame.
      </p>
      <p v-else-if="!selectedProjectId" class="muted">Choose a project to load matching prompts.</p>
      <div v-else class="prompt-grid">
        <article v-for="prompt in recommendedPrompts" :key="prompt.prompt_id" class="prompt-card compact-prompt-card">
          <h3>{{ prompt.question }}</h3>
          <dl>
            <div><dt>Court role</dt><dd>{{ prompt.court_role_target }}</dd></div>
            <div><dt>Situation</dt><dd>{{ prompt.situation_type }}</dd></div>
            <div><dt>Frame</dt><dd>{{ prompt.frame_index }}</dd></div>
            <div><dt>Options</dt><dd>{{ prompt.options.length }}</dd></div>
          </dl>
          <RouterLink class="button small" :to="`/projects/${selectedProjectId}/quiz/${prompt.prompt_id}`">Play</RouterLink>
        </article>
      </div>
    </section>

    <section class="card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">All prompts in this project</p>
          <h2>Project prompt library</h2>
        </div>
        <span class="pill">{{ prompts.length }} total</span>
      </div>
      <p v-if="isLoadingPrompts" class="muted">Loading prompts…</p>
      <p v-else-if="selectedProjectId && !prompts.length" class="muted">No prompts in this project yet.</p>
      <p v-else-if="!selectedProjectId" class="muted">Choose a project to see its full prompt library.</p>
      <div v-else class="prompt-grid">
        <article v-for="prompt in prompts" :key="prompt.prompt_id" class="prompt-card compact-prompt-card">
          <h3>{{ prompt.question }}</h3>
          <dl>
            <div><dt>Court role</dt><dd>{{ prompt.court_role_target }}</dd></div>
            <div><dt>Situation</dt><dd>{{ prompt.situation_type }}</dd></div>
            <div><dt>Frame</dt><dd>{{ prompt.frame_index }}</dd></div>
            <div><dt>Options</dt><dd>{{ prompt.options.length }}</dd></div>
          </dl>
          <RouterLink class="button small" :to="`/projects/${selectedProjectId}/quiz/${prompt.prompt_id}`">Play</RouterLink>
        </article>
      </div>
    </section>
  </template>
</template>

<style scoped>
.training-hero,
.section-heading,
.profile-summary {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.training-hero h1 {
  margin: 0.2rem 0;
}

.profile-summary {
  background: #f8fafc;
}

.profile-summary div {
  display: grid;
  gap: 0.35rem;
}

.profile-summary span {
  color: #334155;
}

select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  display: block;
  margin: 0.5rem 0 1rem;
  padding: 0.75rem;
  width: min(100%, 620px);
}

.pill {
  background: #eef2ff;
  border-radius: 999px;
  color: #1e40af;
  font-weight: 800;
  padding: 0.5rem 0.8rem;
}

.empty-state {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 12px;
  color: #9a3412;
  font-weight: 700;
  padding: 1rem;
}

.prompt-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.compact-prompt-card {
  border: 1px solid #dde3ee;
  border-radius: 12px;
  box-shadow: none;
  display: grid;
  gap: 0.85rem;
  margin: 0;
  padding: 1rem;
}

.compact-prompt-card h3 {
  margin: 0;
}

.compact-prompt-card dl {
  display: grid;
  gap: 0.45rem;
  margin: 0;
}

.compact-prompt-card dl div {
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
}

.compact-prompt-card dt {
  color: #64748b;
  font-weight: 700;
}

.compact-prompt-card dd {
  margin: 0;
  text-align: right;
}

.small {
  font-size: 0.85rem;
  justify-self: start;
  padding: 0.5rem 0.65rem;
}

.muted {
  color: #64748b;
}

@media (max-width: 720px) {
  .training-hero,
  .section-heading,
  .profile-summary {
    display: block;
  }
}
</style>
