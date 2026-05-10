import { readonly, ref } from 'vue'
import { apiClient, isApiClientError } from '../api/client'
import { useProjectStore } from '../stores/projectStore'

const loading = ref(false)
const error = ref<string | null>(null)
const errorCode = ref<string | null>(null)
const errorHint = ref<string | null>(null)
const hydratedProjectIds = new Set<string>()

function hasEnoughData(projectId: string): boolean {
  const projectStore = useProjectStore()
  const project = projectStore.getProject(projectId)
  return !!project && hydratedProjectIds.has(projectId)
}

export function useProjectHydration() {
  const projectStore = useProjectStore()

  async function ensureProjectHydrated(projectId: string): Promise<void> {
    projectStore.setActiveProject(projectId)
    error.value = null
    errorCode.value = null
    errorHint.value = null
    if (hasEnoughData(projectId)) return

    loading.value = true
    try {
      const bundle = await apiClient.getProjectBundle(projectId)
      projectStore.hydrateProjectFromBundle(bundle)
      hydratedProjectIds.add(projectId)
    } catch (hydrationError) {
      if (isApiClientError(hydrationError)) {
        error.value = hydrationError.message
        errorCode.value = hydrationError.code
        errorHint.value = hydrationError.debug_hint ?? null
      } else {
        error.value = hydrationError instanceof Error ? hydrationError.message : 'Could not hydrate project from backend.'
        errorCode.value = 'PROJECT_HYDRATION_ERROR'
        errorHint.value = null
      }
      throw hydrationError
    } finally {
      loading.value = false
    }
  }

  return {
    ensureProjectHydrated,
    loading: readonly(loading),
    error: readonly(error),
    errorCode: readonly(errorCode),
    errorHint: readonly(errorHint)
  }
}
