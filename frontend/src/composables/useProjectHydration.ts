import { readonly, ref } from 'vue'
import { apiClient, isApiClientError } from '../api/client'
import { useProjectStore } from '../stores/projectStore'

const isHydrating = ref(false)
const hydrationError = ref<string | null>(null)
const hydrationErrorCode = ref<string | null>(null)
const hydrationErrorHint = ref<string | null>(null)
const hydratedProjectIds = new Set<string>()

export interface ProjectHydrationOptions {
  force?: boolean
}

function hasBasicMetadata(projectId: string): boolean {
  const projectStore = useProjectStore()
  const project = projectStore.getProject(projectId)
  return !!project?.id && !!project.name
}

export function markProjectHydrationStale(projectId: string) {
  hydratedProjectIds.delete(projectId)
}

export function useProjectHydration() {
  const projectStore = useProjectStore()

  async function ensureProjectHydrated(projectId: string, options: ProjectHydrationOptions = {}): Promise<void> {
    projectStore.setActiveProject(projectId)
    hydrationError.value = null
    hydrationErrorCode.value = null
    hydrationErrorHint.value = null

    if (!options.force && (hydratedProjectIds.has(projectId) || hasBasicMetadata(projectId))) return

    isHydrating.value = true
    try {
      const bundle = await apiClient.getProjectBundle(projectId)
      projectStore.hydrateProjectFromBundle(bundle)
      hydratedProjectIds.add(projectId)
    } catch (error) {
      if (isApiClientError(error)) {
        hydrationError.value = error.message
        hydrationErrorCode.value = error.code
        hydrationErrorHint.value = error.debug_hint ?? null
      } else {
        hydrationError.value = error instanceof Error ? error.message : 'Could not hydrate project from backend.'
        hydrationErrorCode.value = 'PROJECT_HYDRATION_ERROR'
        hydrationErrorHint.value = null
      }
      throw error
    } finally {
      isHydrating.value = false
    }
  }

  return {
    ensureProjectHydrated,
    isHydrating: readonly(isHydrating),
    hydrationError: readonly(hydrationError),
    hydrationErrorCode: readonly(hydrationErrorCode),
    hydrationErrorHint: readonly(hydrationErrorHint),
    // Backward-compatible aliases for existing callers outside the hydrated pages.
    loading: readonly(isHydrating),
    error: readonly(hydrationError),
    errorCode: readonly(hydrationErrorCode),
    errorHint: readonly(hydrationErrorHint)
  }
}
