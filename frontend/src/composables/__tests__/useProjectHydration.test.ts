import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { apiClient, ApiClientError, type ProjectBundleResponse } from '../../api/client'
import { markProjectHydrationStale, useProjectHydration } from '../useProjectHydration'
import { useProjectStore } from '../../stores/projectStore'

function bundle(projectId = 'project-1'): ProjectBundleResponse {
  return {
    project: {
      schema_version: '1.0',
      project_id: projectId,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      name: 'Hydrated Project',
      description: null,
      metadata: {},
      original_input: {},
      pipeline_output: {},
      debug_metadata: {}
    },
    video: null,
    frames: null,
    calibration: null,
    tracking: null,
    projected_tracks: null
  }
}

describe('useProjectHydration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    markProjectHydrationStale('project-1')
    markProjectHydrationStale('project-2')
  })

  it('hydrates a missing project from the backend bundle', async () => {
    vi.spyOn(apiClient, 'getProjectBundle').mockResolvedValue(bundle())
    const { ensureProjectHydrated, hydrationError } = useProjectHydration()

    await ensureProjectHydrated('project-1')

    expect(apiClient.getProjectBundle).toHaveBeenCalledWith('project-1')
    expect(useProjectStore().getProject('project-1')?.name).toBe('Hydrated Project')
    expect(hydrationError.value).toBeNull()
  })

  it('exposes API error state on hydration failure', async () => {
    vi.spyOn(apiClient, 'getProjectBundle').mockRejectedValue(new ApiClientError(404, {
      code: 'PROJECT_NOT_FOUND',
      message: 'Project was not found.',
      details: {},
      debug_hint: 'Create the project first.'
    }))
    const { ensureProjectHydrated, hydrationError, hydrationErrorCode, hydrationErrorHint } = useProjectHydration()

    await expect(ensureProjectHydrated('project-2')).rejects.toThrow('Project was not found.')
    await nextTick()

    expect(hydrationError.value).toBe('Project was not found.')
    expect(hydrationErrorCode.value).toBe('PROJECT_NOT_FOUND')
    expect(hydrationErrorHint.value).toBe('Create the project first.')
  })

  it('skips backend fetch for cached basic metadata unless forced', async () => {
    const getBundle = vi.spyOn(apiClient, 'getProjectBundle').mockResolvedValue(bundle())
    const store = useProjectStore()
    store.addProject({ id: 'project-1', name: 'Cached Project', source: 'upload' })
    const { ensureProjectHydrated } = useProjectHydration()

    await ensureProjectHydrated('project-1')
    expect(getBundle).not.toHaveBeenCalled()

    await ensureProjectHydrated('project-1', { force: true })
    expect(getBundle).toHaveBeenCalledWith('project-1')
  })
})
