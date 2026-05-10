import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, normalizeApiErrorPayload } from '../client'

describe('normalizeApiErrorPayload', () => {
  it('keeps typed API errors intact', () => {
    expect(normalizeApiErrorPayload(404, { code: 'PROJECT_NOT_FOUND', message: 'Missing', details: { project_id: 'x' }, debug_hint: 'Create it first.' })).toEqual({
      code: 'PROJECT_NOT_FOUND',
      message: 'Missing',
      details: { project_id: 'x' },
      debug_hint: 'Create it first.'
    })
  })

  it('fills defaults when response body is not a typed API error', () => {
    expect(normalizeApiErrorPayload(500, null)).toEqual({
      code: 'HTTP_ERROR',
      message: 'API request failed with status 500',
      details: {},
      debug_hint: null
    })
  })
})

describe('apiClient.getProjectBundle', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('requests the backend project bundle endpoint', async () => {
    const payload = {
      project: {
        schema_version: '1.0',
        project_id: 'project-1',
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
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.getProjectBundle('project-1')).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/projects/project-1/bundle', { headers: expect.any(Headers) })
  })
})


describe('apiClient.getDatasetHealth', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('requests the backend dataset health endpoint', async () => {
    const payload = {
      recognition: { warnings: [] },
      decision: { warnings: [] },
      generated_at: '2026-01-01T00:00:00Z'
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.getDatasetHealth()).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/local-lab/datasets/health', { headers: expect.any(Headers) })
  })
})
