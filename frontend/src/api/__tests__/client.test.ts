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
      projected_tracks: null,
      player_aliases: { project_id: 'project-1', aliases: [] }
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


describe('apiClient.getPlayerValueEvidence', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('requests the backend player value evidence endpoint with encoded params', async () => {
    const payload = {
      summary: { project_id: 'project 1', player_key: 'P/1' },
      events: [],
      role_breakdown: [],
      situation_breakdown: [],
      warning_summary: [],
      generated_at: '2026-01-01T00:00:00Z'
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.getPlayerValueEvidence('project 1', 'P/1')).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/local-lab/player-value/project%201/P%2F1/evidence', { headers: expect.any(Headers) })
  })
})

describe('review queue action client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('posts explicit review actions to the item action endpoint', async () => {
    const payload = {
      item: {
        item_id: 'rq-1',
        item_type: 'RECOGNITION_TRACK',
        priority: 'HIGH',
        reason: 'risk',
        recommended_action: 'review',
        status: 'RESOLVED',
        created_at: '2026-01-01T00:00:00Z',
        allowed_actions: ['MARK_TRACK_FALSE_POSITIVE']
      },
      action: {
        action_id: 'review-action-1',
        item_id: 'rq-1',
        item_type: 'RECOGNITION_TRACK',
        action_type: 'MARK_TRACK_FALSE_POSITIVE',
        project_id: 'project-1',
        target_ref: {},
        payload: {},
        note: 'not a player',
        status: 'APPLIED',
        warnings: [],
        created_at: '2026-01-01T00:00:00Z'
      }
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.performReviewAction('rq-1', { action_type: 'MARK_TRACK_FALSE_POSITIVE', note: 'not a player', payload: {} })).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/review-queue/rq-1/actions', {
      method: 'POST',
      headers: expect.any(Headers),
      body: JSON.stringify({ action_type: 'MARK_TRACK_FALSE_POSITIVE', note: 'not a player', payload: {} })
    })
  })

  it('lists review actions with filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue([]) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.listReviewActions({ item_id: 'rq-1', project_id: 'project-1', action_type: 'DISMISS_WITH_NOTE' })).resolves.toEqual([])

    expect(fetchMock).toHaveBeenCalledWith('/api/review-queue/actions?item_id=rq-1&project_id=project-1&action_type=DISMISS_WITH_NOTE', { headers: expect.any(Headers) })
  })
})

describe('drill recommendation client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('builds drill recommendations through the backend endpoint', async () => {
    const payload = {
      schema_version: '1.0',
      generated_at: '2026-01-01T00:00:00Z',
      project_id: 'project-1',
      player_key: 'P1',
      recommendations: [],
      warnings: [],
      catalog_path: 'catalog.json',
      latest_path: 'latest.json'
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.buildDrillRecommendations({ project_id: 'project-1', player_key: 'P1', max_recommendations: 4 })).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/drills/recommendations', {
      method: 'POST',
      headers: expect.any(Headers),
      body: JSON.stringify({ project_id: 'project-1', player_key: 'P1', max_recommendations: 4 })
    })
  })

  it('loads the latest drill recommendations', async () => {
    const payload = {
      schema_version: '1.0',
      generated_at: '2026-01-01T00:00:00Z',
      recommendations: [],
      warnings: [],
      catalog_path: 'catalog.json',
      latest_path: 'latest.json'
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.getLatestDrillRecommendations()).resolves.toEqual(payload)

    expect(fetchMock).toHaveBeenCalledWith('/api/drills/recommendations/latest', { headers: expect.any(Headers) })
  })
})
